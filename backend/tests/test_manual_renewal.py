"""
Tests for P01-06: Audited, Idempotent Manual Renewal Endpoint.
"""

from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import get_async_db
from backend.models import User, Tenant, AuditLog
from backend.core.permissions import Role, Permission
from backend.auth import create_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


@pytest.mark.asyncio
async def test_manual_renewal_flow(async_db_session: AsyncSession):
    # 1. Create a Super Admin user
    admin_user = User(
        username="super_admin_renewal_test",
        email="superadmin@dentix.test",
        hashed_password="hashed_secret",
        role=Role.SUPER_ADMIN.value,
        is_active=True,
        tenant_id=None,
    )
    async_db_session.add(admin_user)

    # 2. Create an expired tenant
    past = datetime.now(timezone.utc) - timedelta(days=10)
    tenant = Tenant(
        name="Expired Dental Clinic",
        is_active=False,
        subscription_status="expired",
        subscription_end_date=past,
        grace_period_until=past,
        plan="trial",
    )
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(admin_user)
    await async_db_session.refresh(tenant)

    token = create_access_token(data={"sub": admin_user.username, "role": admin_user.role})

    # Test via async client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Valid renewal with extension_days = 60
        payload = {
            "extension_days": 60,
            "notes": "Payment received in cash at annual conference.",
            "idempotency_key": "conf_2026_receipt_001"
        }
        resp = await ac.post(f"/api/v1/admin/tenants/{tenant.id}/renew", json=payload, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["subscription_status"] == "active"
        assert data["is_idempotent_duplicate"] is False

        # Verify DB mutation
        await async_db_session.refresh(tenant)
        assert tenant.subscription_status == "active"
        assert tenant.is_active is False
        end_dt = tenant.subscription_end_date.replace(tzinfo=timezone.utc) if tenant.subscription_end_date.tzinfo is None else tenant.subscription_end_date
        assert end_dt > datetime.now(timezone.utc)

        # Verify Audit Log
        res_a = await async_db_session.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == tenant.id,
                AuditLog.action == "SUBSCRIPTION_MANUAL_RENEW"
            )
        )
        audit = res_a.scalar_one_or_none()
        assert audit is not None
        assert audit.performed_by_id == admin_user.id
        assert "request record" in audit.details
        assert "conf_2026_receipt_001" not in audit.details

        # 4. Exact retry with the same durable key returns the stored result.
        resp_repeat = await ac.post(
            f"/api/v1/admin/tenants/{tenant.id}/renew",
            json=payload,
            headers=headers,
        )
        assert resp_repeat.status_code == 200
        assert resp_repeat.json()["data"]["is_idempotent_duplicate"] is True


@pytest.mark.asyncio
async def test_manual_renewal_rejects_past_date(async_db_session: AsyncSession):
    admin_user = User(
        username="admin_past_date_test",
        email="admin_past@dentix.test",
        hashed_password="hashed_secret",
        role=Role.SUPER_ADMIN.value,
        is_active=True,
    )
    tenant = Tenant(name="Clinic Past Date", is_active=True, subscription_status="active")
    async_db_session.add_all([admin_user, tenant])
    await async_db_session.commit()
    await async_db_session.refresh(admin_user)
    await async_db_session.refresh(tenant)

    token = create_access_token(data={"sub": admin_user.username, "role": admin_user.role})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        resp = await ac.post(
            f"/api/v1/admin/tenants/{tenant.id}/renew",
            json={"new_end_date": past, "idempotency_key": "past-date-001"},
            headers=headers
        )
        assert resp.status_code == 400
        assert "must be in the future" in resp.text


@pytest.mark.asyncio
async def test_manual_renewal_requires_super_admin(async_db_session: AsyncSession):
    regular_doctor = User(
        username="doctor_unauthorized",
        email="doctor@dentix.test",
        hashed_password="hashed_secret",
        role=Role.DOCTOR.value,
        is_active=True,
    )
    tenant = Tenant(name="Clinic Unauthorized", is_active=True, subscription_status="active")
    async_db_session.add_all([regular_doctor, tenant])
    await async_db_session.commit()
    await async_db_session.refresh(regular_doctor)
    await async_db_session.refresh(tenant)

    token = create_access_token(data={"sub": regular_doctor.username, "role": regular_doctor.role})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}
        resp = await ac.post(
            f"/api/v1/admin/tenants/{tenant.id}/renew",
            json={"extension_days": 30, "idempotency_key": "unauthorized-001"},
            headers=headers
        )
        assert resp.status_code in {401, 403}
