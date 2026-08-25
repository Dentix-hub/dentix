#!/usr/bin/env python3
"""Create an encrypted, checksummed SQLite or PostgreSQL database backup."""

import argparse
import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.engine import make_url

MAGIC = b"DENTIX-BACKUP-AES256-GCM\x00"


def calculate_sha256(filepath: Path) -> str:
    digest = hashlib.sha256()
    with filepath.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _encryption_key() -> bytes:
    encoded = os.getenv("DENTIX_BACKUP_ENCRYPTION_KEY", "").strip()
    if not encoded:
        raise RuntimeError("DENTIX_BACKUP_ENCRYPTION_KEY is required")
    try:
        key = base64.urlsafe_b64decode(encoded)
    except Exception as exc:
        raise RuntimeError("Backup encryption key must be URL-safe base64") from exc
    if len(key) != 32:
        raise RuntimeError("Backup encryption key must decode to exactly 32 bytes")
    return key


def _postgres_env(db_url: str) -> dict[str, str]:
    url = make_url(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    env = os.environ.copy()
    env.update({"PGHOST": url.host or "localhost", "PGPORT": str(url.port or 5432),
                "PGDATABASE": url.database or "", "PGUSER": url.username or "",
                "PGPASSWORD": url.password or ""})
    return env


def _write_raw_snapshot(raw_path: Path, db_url: str) -> str:
    url = make_url(db_url.replace("sqlite+aiosqlite://", "sqlite://"))
    if url.get_backend_name() == "sqlite":
        source = Path(url.database or "")
        if not source.is_file():
            raise RuntimeError(f"SQLite source database does not exist: {source}")
        with sqlite3.connect(source) as connection, raw_path.open("w", encoding="utf-8") as out:
            for line in connection.iterdump():
                out.write(f"{line}\n")
        return "sqlite"
    if url.get_backend_name() != "postgresql":
        raise RuntimeError(f"Unsupported database engine: {url.get_backend_name()}")
    subprocess.run(
        ["pg_dump", "--format=custom", "--no-owner", "--no-privileges", f"--file={raw_path}"],
        env=_postgres_env(db_url), check=True, capture_output=True,
    )
    if not raw_path.is_file() or raw_path.stat().st_size == 0:
        raise RuntimeError("pg_dump did not create a usable backup")
    return "postgresql"


def _validate_backup_source(db_url: str) -> None:
    """Validate a read-only source without applying restore target rules."""
    if not db_url:
        raise RuntimeError("DATABASE_URL is required for backup")
    try:
        url = make_url(
            db_url.replace("postgresql+asyncpg://", "postgresql://").replace(
                "sqlite+aiosqlite://", "sqlite://"
            )
        )
    except Exception as exc:
        raise RuntimeError("Backup source must be a valid database URL") from exc
    engine = url.get_backend_name()
    if engine not in {"sqlite", "postgresql"}:
        raise RuntimeError(f"Unsupported database engine: {engine}")
    if engine == "postgresql" and not (url.host and url.database and url.username):
        raise RuntimeError("PostgreSQL backup source is incomplete")


def _schema_revision(db_url: str, engine: str) -> str:
    """Read the Alembic revision without exposing connection credentials."""
    if engine == "sqlite":
        url = make_url(db_url.replace("sqlite+aiosqlite://", "sqlite://"))
        with sqlite3.connect(Path(url.database or "")) as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            ).fetchone()
            if not exists:
                return "unversioned"
            row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
            return str(row[0]) if row else "unversioned"

    completed = subprocess.run(
        [
            "psql",
            "--tuples-only",
            "--no-align",
            "--command",
            "SELECT version_num FROM alembic_version",
        ],
        env=_postgres_env(db_url),
        check=True,
        capture_output=True,
        text=True,
    )
    revision = completed.stdout.strip()
    if not revision:
        raise RuntimeError("PostgreSQL source has no Alembic revision")
    return revision


def create_backup(output_dir: Path, database_url: str | None = None) -> Path:
    db_url = database_url or os.getenv("DATABASE_URL", "")
    _validate_backup_source(db_url)
    key = _encryption_key()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    backup_path = output_dir / f"dentix_backup_{timestamp}.dump.enc"
    manifest_path = output_dir / f"dentix_backup_{timestamp}.manifest.json"

    raw_path = None
    encrypted_temp = backup_path.with_suffix(backup_path.suffix + ".tmp")
    try:
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as temp:
            raw_path = Path(temp.name)
        raw_path.chmod(0o600)
        engine = _write_raw_snapshot(raw_path, db_url)
        schema_revision = _schema_revision(db_url, engine)
        nonce = os.urandom(12)
        ciphertext = AESGCM(key).encrypt(nonce, raw_path.read_bytes(), MAGIC)
        encrypted_temp.write_bytes(MAGIC + nonce + ciphertext)
        encrypted_temp.replace(backup_path)
    finally:
        if raw_path and raw_path.exists():
            raw_path.unlink()
        encrypted_temp.unlink(missing_ok=True)

    backup_sha256 = calculate_sha256(backup_path)
    manifest = {
        "format_version": "2.1",
        "timestamp": timestamp,
        "schema_revision": schema_revision,
        "database_engine": engine,
        "encrypted": True,
        "cipher": "AES-256-GCM",
        "key_id": os.getenv("DENTIX_BACKUP_KEY_ID", "local-unversioned")[:120],
        "artifacts": [
            {
                "kind": "database",
                "name": backup_path.name,
                "size_bytes": backup_path.stat().st_size,
                "sha256": backup_sha256,
            }
        ],
        # Compatibility fields retained for existing operators/readers.
        "backup_file": backup_path.name,
        "size_bytes": backup_path.stat().st_size,
        "sha256": backup_sha256,
        "source": "guarded_backup_cli",
    }
    manifest_temp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    try:
        manifest_temp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        manifest_temp.replace(manifest_path)
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise
    finally:
        manifest_temp.unlink(missing_ok=True)
    print(f"[OK] Encrypted backup created: {backup_path}")
    return backup_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Guarded encrypted database backup")
    parser.add_argument("--output-dir", type=Path, default=Path("backups/offline"))
    args = parser.parse_args()
    create_backup(args.output_dir)


if __name__ == "__main__":
    main()
