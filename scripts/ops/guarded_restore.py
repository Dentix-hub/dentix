#!/usr/bin/env python3
"""Verify, decrypt, and restore a guarded backup into an empty local target."""

import argparse
import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.engine import make_url

from backend.core.target_guard import validate_database_target
from scripts.ops.guarded_backup import MAGIC


def calculate_sha256(filepath: Path) -> str:
    digest = hashlib.sha256()
    with filepath.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _key() -> bytes:
    encoded = os.getenv("DENTIX_BACKUP_ENCRYPTION_KEY", "")
    try:
        key = base64.urlsafe_b64decode(encoded)
    except Exception as exc:
        raise RuntimeError("A valid DENTIX_BACKUP_ENCRYPTION_KEY is required") from exc
    if len(key) != 32:
        raise RuntimeError("Backup encryption key must decode to exactly 32 bytes")
    return key


def _manifest_path(backup_file: Path, requested: Path | None) -> Path:
    return requested or backup_file.parent / (backup_file.name.removesuffix(".dump.enc") + ".manifest.json")


def _decrypt(backup_file: Path) -> bytes:
    payload = backup_file.read_bytes()
    if not payload.startswith(MAGIC) or len(payload) <= len(MAGIC) + 12:
        raise RuntimeError("Backup is not a DENTIX encrypted artifact")
    offset = len(MAGIC)
    return AESGCM(_key()).decrypt(payload[offset:offset + 12], payload[offset + 12:], MAGIC)


def _pg_env(db_url: str) -> tuple[dict[str, str], str]:
    url = make_url(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    env = os.environ.copy()
    env.update({"PGHOST": url.host or "localhost", "PGPORT": str(url.port or 5432),
                "PGDATABASE": url.database or "", "PGUSER": url.username or "",
                "PGPASSWORD": url.password or ""})
    return env, url.database or ""


def _restore(raw: bytes, engine: str, db_url: str) -> None:
    url = make_url(db_url.replace("sqlite+aiosqlite://", "sqlite://"))
    if engine == "sqlite":
        if url.get_backend_name() != "sqlite":
            raise RuntimeError("Backup engine and restore target do not match")
        target = Path(url.database or "")
        if target.exists() and target.stat().st_size:
            raise RuntimeError("Restore target must be a new or empty SQLite database")
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(target) as connection:
            connection.executescript(raw.decode("utf-8"))
        return
    if engine != "postgresql" or url.get_backend_name() != "postgresql":
        raise RuntimeError("Backup engine and restore target do not match")
    env, database = _pg_env(db_url)
    count = subprocess.run(
        ["psql", "--tuples-only", "--no-align", "--command",
         "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname='public'"],
        env=env, check=True, capture_output=True, text=True,
    )
    if int(count.stdout.strip() or "0") != 0:
        raise RuntimeError("PostgreSQL restore target must have an empty public schema")
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as temp:
        raw_path = Path(temp.name)
        temp.write(raw)
    raw_path.chmod(0o600)
    try:
        subprocess.run(
            ["pg_restore", "--exit-on-error", "--single-transaction", "--no-owner",
             "--no-privileges", f"--dbname={database}", str(raw_path)],
            env=env, check=True, capture_output=True,
        )
    finally:
        raw_path.unlink(missing_ok=True)


def _validate_decrypted_format(
    raw: bytes,
    engine: str,
    expected_revision: str | None,
) -> None:
    """Prove the authenticated payload is a parseable database artifact."""
    if engine == "sqlite":
        try:
            script = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("SQLite backup payload is not UTF-8 SQL") from exc
        with sqlite3.connect(":memory:") as connection:
            try:
                connection.executescript(script)
            except sqlite3.DatabaseError as exc:
                raise RuntimeError("SQLite backup payload is not restorable SQL") from exc
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError("SQLite backup failed integrity_check")
            if expected_revision and expected_revision != "unversioned":
                try:
                    restored = connection.execute(
                        "SELECT version_num FROM alembic_version"
                    ).fetchone()
                except sqlite3.DatabaseError as exc:
                    raise RuntimeError("SQLite backup is missing alembic_version") from exc
                if not restored or str(restored[0]) != expected_revision:
                    raise RuntimeError("SQLite backup schema revision mismatch")
        return

    if engine != "postgresql":
        raise RuntimeError(f"Unsupported backup database engine: {engine}")
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as temp:
        raw_path = Path(temp.name)
        temp.write(raw)
    raw_path.chmod(0o600)
    try:
        subprocess.run(
            ["pg_restore", "--list", str(raw_path)],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("PostgreSQL backup is not a valid pg_dump archive") from exc
    finally:
        raw_path.unlink(missing_ok=True)


def verify_and_restore(backup_file: Path, manifest_file: Path | None = None,
                       dry_run: bool = True, database_url: str | None = None) -> bool:
    try:
        manifest_path = _manifest_path(backup_file, manifest_file)
        if not backup_file.is_file() or not manifest_path.is_file():
            raise RuntimeError("Backup or integrity manifest is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        actual_sha256 = calculate_sha256(backup_file).lower()
        if manifest.get("sha256", "").lower() != actual_sha256:
            raise RuntimeError("Backup checksum mismatch")
        if manifest.get("format_version") not in {"2.0", "2.1"} or not manifest.get("encrypted"):
            raise RuntimeError("Unsupported or unencrypted backup artifact")
        if manifest.get("format_version") == "2.1":
            artifacts = manifest.get("artifacts")
            if not isinstance(artifacts, list) or len(artifacts) != 1:
                raise RuntimeError("Backup manifest must describe exactly one database artifact")
            artifact = artifacts[0]
            if (
                artifact.get("kind") != "database"
                or artifact.get("name") != backup_file.name
                or int(artifact.get("size_bytes", -1)) != backup_file.stat().st_size
                or str(artifact.get("sha256", "")).lower() != actual_sha256
            ):
                raise RuntimeError("Backup artifact metadata mismatch")
        raw = _decrypt(backup_file)
        if not raw:
            raise RuntimeError("Decrypted backup is empty")
        _validate_decrypted_format(
            raw,
            str(manifest.get("database_engine", "")),
            manifest.get("schema_revision"),
        )
        if dry_run:
            print("[PASS] Checksum, authenticated decryption, format, and schema succeeded")
            return True
        db_url = database_url or os.getenv("DATABASE_URL", "")
        validate_database_target(db_url, is_destructive=True)
        _restore(raw, manifest["database_engine"], db_url)
        print("[OK] Restore completed into guarded empty target")
        return True
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Guarded encrypted database restore")
    parser.add_argument("backup_file", type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--confirm-destructive-restore", action="store_true")
    args = parser.parse_args()
    success = verify_and_restore(args.backup_file, args.manifest,
                                 dry_run=not args.confirm_destructive_restore,
                                 database_url=None)
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
