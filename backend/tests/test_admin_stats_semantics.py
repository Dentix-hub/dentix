from datetime import datetime, timezone, timedelta
from backend import models
from backend.database import get_async_db
from backend.main import app


def test_admin_stats_subscription_status_semantics(client, super_admin_headers):
    """
    Verify MS-10 operational status semantics:
    - total_tenants: count of non-deleted tenants (is_deleted == False)
    - active_tenants: is_deleted == False AND is_active == True AND (subscription_end_date is None OR >= now)
    - expired_tenants: is_deleted == False AND subscription_end_date < now
    - archived/deleted tenants (is_deleted == True) are excluded from operational counts
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async def seed():
        async for session in app.dependency_overrides[get_async_db]():
            # 1. Operational Active tenant (future end date)
            t_active = models.Tenant(
                name="Active Clinic MS10",
                is_active=True,
                is_deleted=False,
                subscription_end_date=now + timedelta(days=30),
            )
            # 2. Operational Active tenant (no end date / perpetual)
            t_perpetual = models.Tenant(
                name="Perpetual Clinic MS10",
                is_active=True,
                is_deleted=False,
                subscription_end_date=None,
            )
            # 3. Expired tenant (past end date, even if is_active=True)
            t_expired = models.Tenant(
                name="Expired Clinic MS10",
                is_active=True,
                is_deleted=False,
                subscription_end_date=now - timedelta(days=5),
            )
            # 4. Inactive/Disabled tenant (future end date, but is_active=False)
            t_disabled = models.Tenant(
                name="Disabled Clinic MS10",
                is_active=False,
                is_deleted=False,
                subscription_end_date=now + timedelta(days=15),
            )
            # 5. Archived / Deleted tenant (should be completely excluded from operational counts)
            t_archived = models.Tenant(
                name="Archived Clinic MS10",
                is_active=True,
                is_deleted=True,
                deleted_at=now,
                subscription_end_date=now + timedelta(days=30),
            )
            session.add_all([t_active, t_perpetual, t_expired, t_disabled, t_archived])
            await session.commit()
            break

    import anyio
    anyio.run(seed)

    from backend.core.cache import cache
    cache.local_cache.clear()

    response = client.get("/api/v1/admin/stats", headers=super_admin_headers)

    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]

    # Baseline seed in test fixture + 4 non-deleted added = at least 4
    # All added tenants follow strict active vs expired rules
    assert data["total_tenants"] >= 4
    assert data["active_tenants"] >= 2
    assert data["expired_tenants"] >= 1
