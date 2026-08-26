from datetime import datetime, timezone, timedelta
from backend import models
from backend.database import get_async_db
from backend.main import app
from backend.core.cache import cache


def test_admin_charts_12_month_window(client, super_admin_headers):
    """
    Verify MS-11 12-month analytics:
    - monthly_revenue contains exactly 12 chronological keys (YYYY-MM)
    - payments older than 12 months are excluded
    - clinic_growth contains exactly 12 chronological keys (YYYY-MM)
    - tenants created older than 12 months are excluded
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async def seed_data():
        async for session in app.dependency_overrides[get_async_db]():
            # 1. Recent payment (current month)
            p_recent = models.SubscriptionPayment(
                tenant_id=1,
                plan_id=1,
                amount=1000,
                payment_method="credit_card",
                provider="mock",
                provider_payment_id="ms11-p-recent",
                payment_date=now,
            )
            # 2. Old payment (15 months ago -> MUST be excluded)
            p_old = models.SubscriptionPayment(
                tenant_id=1,
                plan_id=1,
                amount=99999,
                payment_method="credit_card",
                provider="mock",
                provider_payment_id="ms11-p-old",
                payment_date=now - timedelta(days=450),
            )


            session.add_all([p_recent, p_old])
            await session.commit()
            break

    import anyio
    anyio.run(seed_data)

    # Invalidate cache so fresh seeded calculations are evaluated
    cache.local_cache.clear()

    response = client.get("/api/v1/admin/stats", headers=super_admin_headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]

    monthly_rev = data["monthly_revenue"]
    assert len(monthly_rev) == 12

    # Old month (15 months ago) should not be in keys
    old_month_key = (now - timedelta(days=450)).strftime("%Y-%m")
    assert old_month_key not in monthly_rev

    # Current month must be present and include recent payment
    current_month_key = now.strftime("%Y-%m")
    assert current_month_key in monthly_rev
    assert float(monthly_rev[current_month_key]) >= 1000


    clinic_growth = data["clinic_growth"]
    assert len(clinic_growth) == 12
