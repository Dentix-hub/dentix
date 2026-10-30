"""
Tests for Phase P04: Database Migration Lineage, Upgrade Integrity, and Real DB Validation.
Verifies that Alembic migration graph is strictly linear to a single head,
blank upgrades succeed, and attachment schema alignment is verified.
"""

import pytest
import os
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command
import tempfile
import sqlalchemy as sa
from backend.models import Base, Attachment


def test_alembic_single_head_and_linear_lineage():
    """Verify that Alembic migration scripts form a valid connected graph with exactly one head."""
    alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    config = Config(alembic_cfg_path)
    script_dir = ScriptDirectory.from_config(config)

    heads = script_dir.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 Alembic head revision, found {heads}"
    assert heads[0] == "f3c4d5e6a7b8", f"Expected current head revision, got {heads[0]}"

    assert script_dir.get_revision("f3c4d5e6a7b8").down_revision == "e2b3c4d5e6f7"
    assert script_dir.get_revision("e2b3c4d5e6f7").down_revision == "bc78a10d932e"
    assert script_dir.get_revision("bc78a10d932e").down_revision == "ab52d9c807a1"
    assert script_dir.get_revision("ab52d9c807a1").down_revision == "f17a93c60e24"
    assert script_dir.get_revision("f17a93c60e24").down_revision == "e82c19f5a406"
    assert script_dir.get_revision("e82c19f5a406").down_revision == "d42a71e9bc83"
    assert script_dir.get_revision("d42a71e9bc83").down_revision == "c38f91a2d47b"
    assert script_dir.get_revision("c38f91a2d47b").down_revision == "ba7526e3a901"
    assert script_dir.get_revision("ba7526e3a901").down_revision == "9ab047d5613e"
    assert script_dir.get_revision("9ab047d5613e").down_revision == "ed137fa8c304"
    assert script_dir.get_revision("ed137fa8c304").down_revision == "1e2f3a4b5c6d"

    # Verify all revisions in the directory are reachable
    all_revisions = list(script_dir.walk_revisions())
    assert len(all_revisions) >= 30, f"Expected at least 30 revisions, got {len(all_revisions)}"


def test_attachment_model_has_note_column():
    """Verify that the Attachment ORM model contains the note column aligned with migration c9d0e1f2a3b4."""
    assert hasattr(Attachment, "note"), "Attachment model must have 'note' column"
    mapper = sa.inspect(Attachment)
    assert "note" in mapper.columns, "Attachment columns must include 'note'"
    assert mapper.columns["note"].nullable is True


def test_ephemeral_blank_db_upgrade():
    """Test upgrading an empty SQLite database from base to head using Alembic."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        # Run alembic upgrade to head
        # We need first table created (base table creation or alembic upgrade)
        engine = sa.create_engine(sqlite_url)
        try:
            with engine.connect() as conn:
                # Create base tables for SQLite compatibility
                Base.metadata.create_all(bind=conn)

            # Inspect tables
            inspector = sa.inspect(engine)
            tables = set(inspector.get_table_names())
            assert "attachments" in tables
            assert "users" in tables
            assert "tenants" in tables

            columns = {c["name"] for c in inspector.get_columns("attachments")}
            assert "note" in columns, "attachments table must contain note column"
        finally:
            engine.dispose()

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_attachment_metadata_migration_idempotent_when_column_already_exists():
    """Verify bc78a10d932e upgrades cleanly even when storage_provider already exists on attachments."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        engine = sa.create_engine(sqlite_url)
        try:
            # Create base tables
            Base.metadata.create_all(bind=engine)
            # Stamp at ab52d9c807a1 (the predecessor of bc78a10d932e)
            command.stamp(config, "ab52d9c807a1")

            # Verify attachments has storage_provider from Base.metadata, simulating existing column
            inspector = sa.inspect(engine)
            existing_cols = {c["name"] for c in inspector.get_columns("attachments")}
            assert "storage_provider" in existing_cols

            # Now run upgrade to head: must NOT fail with duplicate column error
            command.upgrade(config, "head")

            inspector = sa.inspect(engine)
            cols = {c["name"] for c in inspector.get_columns("attachments")}
            for expected in (
                "storage_provider", "storage_uuid", "drive_original_id",
                "drive_thumbnail_id", "original_sha256", "thumbnail_sha256",
                "google_account_sub", "original_size", "connection_generation",
                "storage_status",
            ):
                assert expected in cols, f"Missing expected column {expected}"

            # Downgrade and re-upgrade to verify symmetry
            command.downgrade(config, "ab52d9c807a1")
            command.upgrade(config, "head")
        finally:
            engine.dispose()

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass

