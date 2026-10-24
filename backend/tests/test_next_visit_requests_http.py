import pytest
from httpx import AsyncClient, ASGITransport

from backend import models
from backend.main import app
from backend.auth import create_access_token
from backend.services.feature_service import FeatureFlagService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES


@pytest.mark.asyncio
async def test_get_next_visit_requests_http(async_db_session):
    tenant = models.Tenant(name="NVR Test Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    user = models.User(
        username="receptionist_nvr",
        email="receptionist_nvr@example.com",
        role="receptionist",
        tenant_id=tenant.id,
        hashed_password="hash",
    )
    async_db_session.add(user)
    await async_db_session.commit()

    token = create_access_token(data={"sub": user.username, "tenant_id": tenant.id, "role": user.role})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Native writes OFF (default): fail-closed gate returns 404
        resp_off = await ac.get(
            "/api/v1/next-visit-requests?status=all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_off.status_code == 404
        assert resp_off.json()["detail"] == "Clinical native writes are disabled"

        # 2. Native writes ON: returns 200 with queue items
        # Ensure flag definition exists
        from sqlalchemy import select
        flag_stmt = select(models.FeatureFlag).where(models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES)
        existing_flag = (await async_db_session.execute(flag_stmt)).scalar_one_or_none()
        if not existing_flag:
            async_db_session.add(models.FeatureFlag(
                key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
                description="Clinical native writes",
                is_global_enabled=False,
            ))
            await async_db_session.commit()

        await FeatureFlagService.set_tenant_override(
            async_db_session, tenant.id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True
        )

        resp_on = await ac.get(
            "/api/v1/next-visit-requests?status=all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_on.status_code == 200
        res_data = resp_on.json()
        assert res_data["success"] is True
        assert res_data["data"] == []
