from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend import crud, schemas
from backend.routers import insurance, price_lists, settings


def _result(first=None):
    result = MagicMock()
    result.scalars.return_value.first.return_value = first
    return result


def test_backup_oauth_state_is_signed_identity_bound_and_rejects_raw_legacy_state():
    user = SimpleNamespace(id=17, role="admin", tenant_id=9)
    state = settings._create_backup_oauth_state(user)

    assert state != "user_17"
    payload = settings._decode_backup_oauth_state(state)
    assert payload["user_id"] == 17
    assert payload["tenant_id"] == 9
    assert payload["role"] == "admin"
    assert payload["purpose"] == "google_drive_backup"
    assert payload["nonce"]

    with pytest.raises(HTTPException) as exc:
        settings._decode_backup_oauth_state("user_17")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_tenant_cannot_update_global_procedure():
    db = AsyncMock()
    db.execute.return_value = _result(None)
    procedure = schemas.ProcedureCreate(name="Global Template", price=100)

    result = await crud.update_procedure(db, 5, procedure, tenant_id=7)

    assert result is None
    sql = str(db.execute.await_args.args[0])
    assert "procedures.tenant_id =" in sql
    assert "IS NULL" not in sql.upper()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_tenant_cannot_delete_global_procedure_or_references():
    db = AsyncMock()
    db.execute.return_value = _result(None)

    result = await crud.delete_procedure(db, 5, tenant_id=7)

    assert result is None
    assert db.execute.await_count == 1
    sql = str(db.execute.await_args.args[0])
    assert "procedures.tenant_id =" in sql
    assert "IS NULL" not in sql.upper()
    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_price_list_procedure_guard_rejects_cross_tenant_id():
    db = AsyncMock()
    db.execute.return_value = _result(None)

    with pytest.raises(HTTPException) as exc:
        await price_lists._require_visible_procedure(db, procedure_id=99, tenant_id=7)

    assert exc.value.status_code == 404
    sql = str(db.execute.await_args.args[0])
    assert "procedures.tenant_id" in sql


@pytest.mark.asyncio
async def test_insurance_creation_rejects_missing_tenant_before_database_write():
    db = AsyncMock()
    user = SimpleNamespace(id=1, role="super_admin", tenant_id=None)
    data = insurance.InsuranceProviderCreate(name="Provider")

    with pytest.raises(HTTPException) as exc:
        await insurance.create_insurance_provider(data=data, db=db, current_user=user)

    assert exc.value.status_code == 400
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
