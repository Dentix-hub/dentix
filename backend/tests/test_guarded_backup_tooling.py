"""Guarded backup encryption, integrity, and real SQLite round-trip tests."""

import base64
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from scripts.ops.guarded_backup import MAGIC, calculate_sha256, create_backup
from scripts.ops.guarded_restore import verify_and_restore


def _configure(monkeypatch, tmp_path: Path) -> tuple[str, Path]:
    monkeypatch.setenv(
        "DENTIX_BACKUP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(b"k" * 32).decode(),
    )
    source = tmp_path / "dentix_test_source.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES ('e3a4b5c6d7e8')")
        connection.execute("CREATE TABLE proof (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO proof(value) VALUES ('round-trip')")
        connection.execute("CREATE TABLE tenants (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute(
            "CREATE TABLE patients (id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, name TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE attachments (id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, "
            "patient_id INTEGER NOT NULL, filename TEXT NOT NULL, sha256 TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO tenants(id, name) VALUES (?, ?)",
            [(1, "A"), (2, "B")],
        )
        connection.executemany(
            "INSERT INTO patients(id, tenant_id, name) VALUES (?, ?, ?)",
            [(11, 1, "Patient A"), (21, 2, "Patient B")],
        )
        connection.executemany(
            "INSERT INTO attachments(id, tenant_id, patient_id, filename, sha256) "
            "VALUES (?, ?, ?, ?, ?)",
            [(111, 1, 11, "a.pdf", "a" * 64), (211, 2, 21, "b.pdf", "b" * 64)],
        )
    return f"sqlite:///{source.as_posix()}", source


def test_backup_is_encrypted_and_manifest_is_authenticatable(monkeypatch, tmp_path):
    db_url, _ = _configure(monkeypatch, tmp_path)
    backup_file = create_backup(tmp_path / "backups", db_url)
    manifest_file = backup_file.parent / f"{backup_file.name.removesuffix('.dump.enc')}.manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    assert backup_file.exists()
    assert b"round-trip" not in backup_file.read_bytes()
    assert manifest["sha256"] == calculate_sha256(backup_file)
    assert manifest["format_version"] == "2.1"
    assert manifest["cipher"] == "AES-256-GCM"
    assert manifest["schema_revision"] == "e3a4b5c6d7e8"
    assert manifest["artifacts"][0]["name"] == backup_file.name
    assert verify_and_restore(backup_file, manifest_file, dry_run=True)


def test_restore_verification_detects_tampering(monkeypatch, tmp_path):
    db_url, _ = _configure(monkeypatch, tmp_path)
    backup_file = create_backup(tmp_path / "backups", db_url)
    manifest_file = backup_file.parent / f"{backup_file.name.removesuffix('.dump.enc')}.manifest.json"
    backup_file.write_bytes(backup_file.read_bytes() + b"tampered")

    assert verify_and_restore(backup_file, manifest_file, dry_run=True) is False


def test_real_sqlite_backup_restore_round_trip(monkeypatch, tmp_path):
    db_url, _ = _configure(monkeypatch, tmp_path)
    backup_file = create_backup(tmp_path / "backups", db_url)
    target = tmp_path / "dentix_test_restored.db"
    monkeypatch.setenv("LOCAL_DESTRUCTIVE_TESTS", "1")

    assert verify_and_restore(
        backup_file,
        dry_run=False,
        database_url=f"sqlite:///{target.as_posix()}",
    )
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT value FROM proof").fetchone() == ("round-trip",)
        assert connection.execute("SELECT COUNT(*) FROM tenants").fetchone() == (2,)
        assert connection.execute("SELECT COUNT(*) FROM patients").fetchone() == (2,)
        assert connection.execute("SELECT COUNT(*) FROM attachments").fetchone() == (2,)
        assert connection.execute(
            "SELECT tenant_id, patient_id, filename, sha256 FROM attachments ORDER BY id"
        ).fetchall() == [
            (1, 11, "a.pdf", "a" * 64),
            (2, 21, "b.pdf", "b" * 64),
        ]
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "e3a4b5c6d7e8",
        )


def test_restore_missing_manifest_fails(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "DENTIX_BACKUP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(b"k" * 32).decode(),
    )
    missing = tmp_path / "dentix_test_missing.dump.enc"
    missing.write_bytes(b"not a backup")
    assert verify_and_restore(missing, tmp_path / "missing.json", dry_run=True) is False


def test_restore_verification_rejects_wrong_key(monkeypatch, tmp_path):
    db_url, _ = _configure(monkeypatch, tmp_path)
    backup_file = create_backup(tmp_path / "backups", db_url)
    monkeypatch.setenv(
        "DENTIX_BACKUP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(b"z" * 32).decode(),
    )
    assert verify_and_restore(backup_file, dry_run=True) is False


def test_restore_verification_rejects_authenticated_wrong_format(monkeypatch, tmp_path):
    key = b"k" * 32
    monkeypatch.setenv(
        "DENTIX_BACKUP_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(key).decode(),
    )
    nonce = os.urandom(12)
    payload = MAGIC + nonce + AESGCM(key).encrypt(nonce, b"not a sqlite dump", MAGIC)
    backup_file = tmp_path / "dentix_test_wrong_format.dump.enc"
    backup_file.write_bytes(payload)
    sha256 = hashlib.sha256(payload).hexdigest()
    manifest_file = tmp_path / "dentix_test_wrong_format.manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "format_version": "2.1",
                "schema_revision": "e3a4b5c6d7e8",
                "database_engine": "sqlite",
                "encrypted": True,
                "sha256": sha256,
                "artifacts": [
                    {
                        "kind": "database",
                        "name": backup_file.name,
                        "size_bytes": backup_file.stat().st_size,
                        "sha256": sha256,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert verify_and_restore(backup_file, manifest_file, dry_run=True) is False


def test_restore_rejects_unsafe_target(monkeypatch, tmp_path):
    db_url, _ = _configure(monkeypatch, tmp_path)
    backup_file = create_backup(tmp_path / "backups", db_url)
    monkeypatch.setenv("LOCAL_DESTRUCTIVE_TESTS", "1")
    unsafe = tmp_path / "production.db"
    assert verify_and_restore(
        backup_file,
        dry_run=False,
        database_url=f"sqlite:///{unsafe.as_posix()}",
    ) is False


def test_restore_rejects_backup_target_engine_mismatch(monkeypatch, tmp_path):
    db_url, _ = _configure(monkeypatch, tmp_path)
    backup_file = create_backup(tmp_path / "backups", db_url)
    monkeypatch.setenv("LOCAL_DESTRUCTIVE_TESTS", "1")
    assert verify_and_restore(
        backup_file,
        dry_run=False,
        database_url="postgresql://restore_user@localhost/dentix_test",
    ) is False
