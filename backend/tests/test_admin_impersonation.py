"""
Unit tests for Super Admin impersonation request contract (MS-03).
"""

from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock
from backend.routers.admin_tenants import impersonate_tenant
from backend.models.user import User
from backend.models.tenant import Tenant
from jose import jwt
from backend.auth import SECRET_KEY, ALGORITHM


@pytest.mark.asyncio
async def test_impersonate_tenant_missing_reason_raises_400():
    request = MagicMock()
    current_user = User(id=1, username="superadmin", role="super_admin")
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await impersonate_tenant(
            tenant_id=10,
            request=request,
            user_id=None,
            reason="",
            scope="read_only",
            current_user=current_user,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert "سبب انتحال الشخصية مطلوب" in exc_info.value.detail


@pytest.mark.asyncio
async def test_impersonate_tenant_short_reason_raises_400():
    request = MagicMock()
    current_user = User(id=1, username="superadmin", role="super_admin")
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await impersonate_tenant(
            tenant_id=10,
            request=request,
            user_id=None,
            reason="test",  # 4 chars < 5 chars
            scope="read_only",
            current_user=current_user,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert "5 أحرف على الأقل" in exc_info.value.detail


@pytest.mark.asyncio
async def test_impersonate_tenant_valid_reason_returns_token(monkeypatch):
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers.get.return_value = "pytest"

    current_user = User(id=1, username="superadmin", role="super_admin")
    tenant = Tenant(id=10, name="Test Clinic")
    target_user = User(id=5, username="doctor_john", role="doctor", tenant_id=10, tenant=tenant)

    db = AsyncMock()
    system_db = AsyncMock()
    system_db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = target_user
    mock_result.scalar_one_or_none.return_value = target_user
    system_db.execute.return_value = mock_result

    @asynccontextmanager
    async def fake_system_session_scope():
        yield system_db

    monkeypatch.setattr(
        "backend.routers.admin_tenants.system_session_scope",
        fake_system_session_scope,
    )

    response = await impersonate_tenant(
        tenant_id=10,
        request=request,
        user_id=5,
        reason="استكشاف مشكلة فنية في النظام",
        scope="read_only",
        current_user=current_user,
        db=db,
    )

    data = response["data"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["tenant_name"] == "Test Clinic"
    assert data["target_user"] == "doctor_john"
    assert data["scope"] == "read_only"

    # Decode and verify token payload claims
    payload = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload is not None
    assert payload.get("is_impersonating") is True
    assert payload.get("impersonation_scope") == "read_only"
    assert payload.get("tenant_id") == 10
    assert payload.get("sub") == "doctor_john"
    db.execute.assert_not_awaited()
    system_db.execute.assert_awaited_once()
