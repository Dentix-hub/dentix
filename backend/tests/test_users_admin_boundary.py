from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from backend.routers import users as users_router


def _user(*, user_id=1, role="admin", tenant_id=7):
    return SimpleNamespace(id=user_id, role=role, tenant_id=tenant_id, username=f"user-{user_id}")


def test_manager_cannot_use_tenant_user_admin_boundary():
    with pytest.raises(HTTPException) as exc:
        users_router._require_tenant_user_admin(_user(role="manager"))

    assert exc.value.status_code == 403
    assert exc.value.detail == "Admin access required"


def test_platform_context_without_tenant_is_rejected():
    with pytest.raises(HTTPException) as exc:
        users_router._require_tenant_user_admin(_user(role="super_admin", tenant_id=None))

    assert exc.value.status_code == 400


def test_tenant_user_management_cannot_assign_super_admin_role():
    with pytest.raises(HTTPException) as exc:
        users_router._validate_tenant_role("super_admin")

    assert exc.value.status_code == 403
    assert "platform role" in exc.value.detail


def test_normal_tenant_roles_remain_allowed():
    for role in ["admin", "manager", "doctor", "assistant", "receptionist", "nurse", "accountant"]:
        users_router._validate_tenant_role(role)


@pytest.mark.asyncio
async def test_delete_user_returns_404_when_tenant_user_does_not_exist(monkeypatch):
    delete_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(users_router.crud, "delete_user", delete_mock)

    with pytest.raises(HTTPException) as exc:
        await users_router.delete_user(
            user_id=99,
            db=AsyncMock(),
            current_user=_user(user_id=1, role="admin", tenant_id=7),
        )

    assert exc.value.status_code == 404
    delete_mock.assert_awaited_once_with(delete_mock.await_args.args[0], 99, 7)


@pytest.mark.asyncio
async def test_admin_cannot_delete_own_active_account(monkeypatch):
    delete_mock = AsyncMock()
    monkeypatch.setattr(users_router.crud, "delete_user", delete_mock)
    admin = _user(user_id=5, role="admin", tenant_id=7)

    with pytest.raises(HTTPException) as exc:
        await users_router.delete_user(user_id=5, db=AsyncMock(), current_user=admin)

    assert exc.value.status_code == 400
    delete_mock.assert_not_awaited()
