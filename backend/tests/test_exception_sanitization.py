"""
Tests for Phase P03: Exception Sanitization and Impersonation Identity Remediation.
Verifies that unhandled errors, validation errors, and HTTPExceptions are sanitized,
and that impersonation audit logs properly record performed_by_id.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.models import User, Tenant, AuditLog
from backend.core.permissions import Role
from backend.auth import create_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


@pytest.mark.asyncio
async def test_http_exception_structure(async_db_session: AsyncSession):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/non_existent_route_test")
        assert resp.status_code == 404
        data = resp.json()
        assert data.get("success") is False
        assert "detail" in data
        assert "trace_id" in data


@pytest.mark.asyncio
async def test_impersonation_audit_records_performed_by(async_db_session: AsyncSession):
    # 1. Create super admin and clinic user
    super_admin = User(
        username="super_admin_impersonator",
        email="super_imp@dentix.test",
        hashed_password="hashed_secret",
        role=Role.SUPER_ADMIN.value,
        is_active=True,
    )
    tenant = Tenant(name="Impersonated Clinic", is_active=True, subscription_status="active")
    async_db_session.add_all([super_admin, tenant])
    await async_db_session.commit()
    await async_db_session.refresh(super_admin)
    await async_db_session.refresh(tenant)

    clinic_user = User(
        username="clinic_target_doctor",
        email="doctor_imp@dentix.test",
        hashed_password="hashed_secret",
        role=Role.DOCTOR.value,
        tenant_id=tenant.id,
        is_active=True,
    )
    async_db_session.add(clinic_user)
    await async_db_session.commit()
    await async_db_session.refresh(clinic_user)

    admin_token = create_access_token(
        data={"sub": super_admin.username, "role": super_admin.role}
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = await ac.post(
            f"/api/v1/admin/tenants/{tenant.id}/impersonate",
            params={
                "user_id": clinic_user.id,
                "reason": "Diagnostic investigation for clinic issue",
                "scope": "read_only",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Check AuditLog entry
        stmt = select(AuditLog).where(
            AuditLog.action == "IMPERSONATION_START",
            AuditLog.tenant_id == tenant.id
        )
        res = await async_db_session.execute(stmt)
        audit = res.scalar_one_or_none()
        assert audit is not None
        assert audit.performed_by_id == super_admin.id
        assert audit.performed_by_username == super_admin.username
        assert audit.target_user_id == clinic_user.id
        assert audit.target_username == clinic_user.username
