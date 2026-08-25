"""
Tests for Phase P08: Guarded Offline CLI Tooling & Round-Trip Verification.
"""

import json
import tempfile
from pathlib import Path
from scripts.ops.guarded_backup import create_backup, calculate_sha256
from scripts.ops.guarded_restore import verify_and_restore


def test_backup_creates_manifest_and_verifies_checksum():
    with tempfile.TemporaryDirectory(dir="backend/tests") as temp_dir:
        out_dir = Path(temp_dir) / "backups"
        backup_file = create_backup(out_dir)

        assert backup_file.exists()
        manifest_file = backup_file.parent / f"{backup_file.stem}.manifest.json"
        assert manifest_file.exists()

        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest_data["sha256"] == calculate_sha256(backup_file)
        assert manifest_data["format_version"] == "1.0"


def test_restore_verification_detects_tampering():
    with tempfile.TemporaryDirectory(dir="backend/tests") as temp_dir:
        out_dir = Path(temp_dir) / "backups"
        backup_file = create_backup(out_dir)
        manifest_file = backup_file.parent / f"{backup_file.stem}.manifest.json"

        # 1. Untampered backup passes dry-run restore
        assert verify_and_restore(backup_file, manifest_file, dry_run=True) is True

        # 2. Tampered backup fails integrity verification
        backup_file.write_text("TAMPERED DATA IN FILE", encoding="utf-8")
        assert verify_and_restore(backup_file, manifest_file, dry_run=True) is False


def test_restore_missing_manifest_fails():
    with tempfile.TemporaryDirectory(dir="backend/tests") as temp_dir:
        dummy_sql = Path(temp_dir) / "fake.sql"
        dummy_sql.write_text("SELECT 1;", encoding="utf-8")
        assert verify_and_restore(dummy_sql, manifest_file=Path(temp_dir) / "nonexistent.json", dry_run=True) is False
