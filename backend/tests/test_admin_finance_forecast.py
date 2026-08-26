from datetime import datetime, timezone, timedelta
from backend import models
from backend.database import get_async_db
from backend.main import app
from backend.core.cache import cache


def test_admin_finance_forecast_and_overdue_semantics(client, super_admin_headers):
    """
    Verify MS-12 finance forecast semantics:
    - forecast reflects active unexpired non-deleted subscriptions only
    - expired and deleted subscriptions are excluded from forecast
    - overdue clinics includes only expired and non-deleted clinics
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async def seed_data():
        async for session in app.dependency_overrides[get_async_db]():
            plan_500 = models.SubscriptionPlan(
                name="ms12-plan-500",
                display_name_ar="خطة 500",
                price=500.0,
            )
            plan_1000 = models.SubscriptionPlan(
                name="ms12-plan-1000",
                display_name_ar="خطة 1000",
                price=1000.0,
            )
            session.add_all([plan_500, plan_1000])
            await session.commit()
            await session.refresh(plan_500)
            await session.refresh(plan_1000)

            # 1. Active unexpired tenant -> INCLUDED in forecast (500)
            t_active = models.Tenant(
                name="Active Forecast Clinic",
                plan_id=plan_500.id,
                is_active=True,
                is_deleted=False,
                subscription_end_date=now + timedelta(days=30),
            )
            # 2. Expired tenant -> EXCLUDED from forecast, INCLUDED in overdue
            t_expired = models.Tenant(
                name="Expired Overdue Clinic",
                plan_id=plan_1000.id,
                is_active=True,
                is_deleted=False,
                subscription_end_date=now - timedelta(days=10),
            )
            # 3. Deleted tenant -> EXCLUDED from forecast and overdue
            t_deleted = models.Tenant(
                name="Deleted Clinic",
                plan_id=plan_1000.id,
                is_active=True,
                is_deleted=True,
                subscription_end_date=now + timedelta(days=30),
            )

            session.add_all([t_active, t_expired, t_deleted])
            await session.commit()
            break

    import anyio
    anyio.run(seed_data)

    cache.local_cache.clear()

    response = client.get("/api/v1/admin/finance/reports", headers=super_admin_headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]

    # Forecast must be >= 500 (our active tenant) and must NOT include t_expired (1000) or t_deleted (1000)
    assert data["monthly_forecast"] >= 500.0

    # Overdue clinics must contain our expired clinic
    overdue_names = [c["name"] for c in data["overdue_clinics"]]
    assert "Expired Overdue Clinic" in overdue_names
    assert "Deleted Clinic" not in overdue_names
    assert "Active Forecast Clinic" not in overdue_names
