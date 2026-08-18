from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend import schemas
from backend.routers import appointments as appointments_router


def _user():
    return SimpleNamespace(id=7, tenant_id=11, role="admin", username="owner")


def _request(path: str):
    return SimpleNamespace(url=SimpleNamespace(path=path))


def _db():
    db = MagicMock()
    db.rollback = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_update_appointment_preserves_not_found_http_exception(monkeypatch):
    db = _db()
    monkeypatch.setattr(
        appointments_router.crud,
        "update_appointment",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await appointments_router.update_appointment(
            request=_request("/api/v1/appointments/999"),
            appointment_id=999,
            appointment=schemas.AppointmentUpdate(notes="changed"),
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Appointment not found"


@pytest.mark.asyncio
async def test_update_appointment_status_does_not_false_succeed_when_missing(monkeypatch):
    db = _db()
    audit = MagicMock()
    monkeypatch.setattr(appointments_router, "log_admin_action", audit)
    monkeypatch.setattr(
        appointments_router.crud,
        "update_appointment_status",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await appointments_router.update_appointment_status(
            appointment_id=999,
            status="Completed",
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 404
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_appointment_does_not_false_succeed_when_missing(monkeypatch):
    db = _db()
    audit = MagicMock()
    monkeypatch.setattr(appointments_router, "log_admin_action", audit)
    monkeypatch.setattr(
        appointments_router.crud,
        "delete_appointment",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await appointments_router.delete_appointment(
            appointment_id=999,
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 404
    db.rollback.assert_awaited_once()
