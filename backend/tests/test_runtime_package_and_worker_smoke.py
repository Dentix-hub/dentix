"""Regression tests for runtime packaging, outbox event processor flow, and container smoke."""

import os
import subprocess
import sys
import tempfile
import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend import models
from backend.services.event_service import event_service
from backend.workers.event_processor import event_processor_flow, _handlers
import backend.workers.handlers  # noqa: F401


def test_runtime_image_import_graph_succeeds_with_packaged_scripts(tmp_path):
    """Simulate the runtime container layout (/app containing backend/ and scripts/ops/).

    Verify that scheduler, registered handlers, guarded_backup, and guarded_restore
    import cleanly without the repository root in sys.path.
    """
    repo_root = Path(__file__).resolve().parents[2]
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Create directory symlinks/junctions or copies for backend and scripts/ops
    # To be fully cross-platform and reliable without privilege, copy the directories
    import shutil
    shutil.copytree(repo_root / "backend", app_dir / "backend", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
    (app_dir / "scripts" / "ops").mkdir(parents=True)
    shutil.copy2(repo_root / "scripts" / "ops" / "__init__.py", app_dir / "scripts" / "ops" / "__init__.py")
    shutil.copy2(repo_root / "scripts" / "ops" / "guarded_backup.py", app_dir / "scripts" / "ops" / "guarded_backup.py")
    shutil.copy2(repo_root / "scripts" / "ops" / "guarded_restore.py", app_dir / "scripts" / "ops" / "guarded_restore.py")

    code = (
        "import sys\n"
        "from backend.services.backup_scheduler_service import schedule_due_backup, execute_backup_event\n"
        "import backend.workers.event_processor\n"
        "import backend.workers.handlers\n"
        "from scripts.ops.guarded_backup import create_backup\n"
        "from scripts.ops.guarded_restore import verify_and_restore\n"
        "print('CONTAINER_IMPORTS_OK')\n"
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(app_dir)
    env["ENVIRONMENT"] = "production"

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(app_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Import check failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    assert "CONTAINER_IMPORTS_OK" in result.stdout


def test_old_image_environment_fails_without_scripts_package(tmp_path):
    """Simulate the old container layout (/app containing backend/ but NO scripts/ops/).

    Verify that importing scripts.ops.guarded_backup in the old layout fails with
    ModuleNotFoundError: No module named 'scripts'.
    """
    repo_root = Path(__file__).resolve().parents[2]
    app_dir = tmp_path / "app_old"
    app_dir.mkdir()

    import shutil
    shutil.copytree(repo_root / "backend", app_dir / "backend", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))

    code = "from scripts.ops.guarded_backup import create_backup\n"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(app_dir)
    env["ENVIRONMENT"] = "production"

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(app_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ModuleNotFoundError: No module named 'scripts" in result.stderr


def test_scheduler_import_and_disabled_call_succeeds_without_scripts(tmp_path):
    """Simulate importing scheduler and calling schedule_due_backup when disabled.

    With deferred execution import, importing the scheduler module does not fail
    merely due to missing scripts.ops.
    """
    repo_root = Path(__file__).resolve().parents[2]
    app_dir = tmp_path / "app_no_scripts"
    app_dir.mkdir()

    import shutil
    shutil.copytree(repo_root / "backend", app_dir / "backend", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))

    code = (
        "import asyncio\n"
        "from backend.services.backup_scheduler_service import schedule_due_backup\n"
        "print('SCHEDULER_IMPORT_OK')\n"
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(app_dir)
    env["ENVIRONMENT"] = "production"

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(app_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Scheduler import failed:\nSTDERR: {result.stderr}"
    assert "SCHEDULER_IMPORT_OK" in result.stdout


@pytest.mark.asyncio
async def test_event_processor_flow_resilient_to_scheduler_failure(
    async_db_session: AsyncSession, monkeypatch
):
    """Ensure a failing scheduler does not block pending outbox event processing."""
    from backend.services import backup_scheduler_service

    async def _failing_schedule(_session, **_kwargs):
        raise RuntimeError("Synthetic platform scheduler breakdown")

    monkeypatch.setattr(backup_scheduler_service, "schedule_due_backup", _failing_schedule)

    tenant = models.Tenant(name="Outbox Resilience Clinic", is_active=True, subscription_status="active")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    event = event_service.emit_event(
        db=async_db_session,
        event_type="appointment.created",
        aggregate_type="Appointment",
        aggregate_id="1001",
        payload={"patient_id": 1, "time": "2026-10-28T12:00:00Z"},
        tenant_id=tenant.id,
    )
    await async_db_session.commit()
    await async_db_session.refresh(event)

    # Monkeypatch system_session_scope to yield our async_db_session for testing
    from contextlib import asynccontextmanager
    import backend.workers.event_processor as ep

    @asynccontextmanager
    async def mock_system_session():
        yield async_db_session

    monkeypatch.setattr(ep, "system_session_scope", mock_system_session)

    # Flow should complete without raising and process the pending event
    await event_processor_flow()

    await async_db_session.refresh(event)
    assert event.status == "completed"
    assert event.processed_at is not None


@pytest.mark.asyncio
async def test_event_processor_flow_processes_and_completes_outbox_event(
    async_db_session: AsyncSession, monkeypatch
):
    """Verify that event_processor_flow processes a pending event end-to-end."""
    tenant = models.Tenant(name="Outbox E2E Clinic", is_active=True, subscription_status="active")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    event = event_service.emit_event(
        db=async_db_session,
        event_type="treatment.created",
        aggregate_type="Treatment",
        aggregate_id="2002",
        payload={"patient_id": 2, "procedure": "Scaling"},
        tenant_id=tenant.id,
    )
    await async_db_session.commit()
    await async_db_session.refresh(event)

    from contextlib import asynccontextmanager
    import backend.workers.event_processor as ep

    @asynccontextmanager
    async def mock_system_session():
        yield async_db_session

    monkeypatch.setattr(ep, "system_session_scope", mock_system_session)

    await event_processor_flow()

    await async_db_session.refresh(event)
    assert event.status == "completed"
    assert event.processed_at is not None


@pytest.mark.asyncio
async def test_all_handlers_registered_and_archive_safety_gate_intact(async_db_session: AsyncSession):
    """Verify registered handlers and that pending image operations trigger archive safety gate."""
    expected_handlers = {
        "appointment.created",
        "appointment.cancelled",
        "payment.created",
        "treatment.created",
        "system.backup.requested",
        "auth.password_reset.requested",
        "tenant.restore.confirmed",
        "tenant.backup.requested",
        "tenant.image.upload",
        "tenant.image.delete",
        "tenant.image.cleanup",
    }
    for h in expected_handlers:
        assert h in _handlers, f"Handler {h} must be registered"

    from backend.services.drive_image_safety import ensure_no_active_image_operations
    from backend.services.tenant_archive import ArchiveError

    tenant = models.Tenant(name="Safety Gate Clinic", is_active=True, subscription_status="active")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    patient = models.Patient(tenant_id=tenant.id, name="Gate Patient", age=30, phone="0500000000", medical_history="None", notes="")
    async_db_session.add(patient)
    await async_db_session.commit()
    await async_db_session.refresh(patient)

    # With no active operations, gate passes
    await ensure_no_active_image_operations(async_db_session, tenant.id)

    # With a pending image attachment, gate must raise ArchiveError
    attachment = models.Attachment(
        tenant_id=tenant.id,
        patient_id=patient.id,
        filename="xray.jpg",
        file_type="image/jpeg",
        file_path="/tmp/xray.jpg",
        storage_provider="google_drive",
        storage_status="pending",
    )
    async_db_session.add(attachment)
    await async_db_session.commit()

    with pytest.raises(ArchiveError, match="Google Drive"):
        await ensure_no_active_image_operations(async_db_session, tenant.id)
