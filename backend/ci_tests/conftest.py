"""Fixtures for PostgreSQL-only CI tests."""

import os

import psycopg2
import pytest
import pytest_asyncio

from backend.database import async_engine


@pytest.fixture(scope="session", autouse=True)
def subscription_payment_rls_contract():
    """Prove subscription payments are isolated by the real PostgreSQL policy."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith(("postgresql://", "postgres://")):
        yield
        return

    tenant_a = 99365
    tenant_b = 99366
    plan_id = 993650
    payment_a = 993651
    payment_b = 993661

    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            # The CI role is NOBYPASSRLS. Use the application's explicit
            # maintenance GUC only while seeding deterministic parent rows.
            cursor.execute(
                "SELECT set_config('rls.bypass_rls', 'true', true)"
            )
            cursor.execute(
                """
                INSERT INTO tenants (
                    id, name, subscription_status, plan, is_active,
                    created_at, total_revenue, backup_frequency, timezone
                )
                VALUES
                    (%s, 'RLS Contract Tenant A', 'active', 'trial', TRUE, NOW(), 0, 'off', 'Africa/Cairo'),
                    (%s, 'RLS Contract Tenant B', 'active', 'trial', TRUE, NOW(), 0, 'off', 'Africa/Cairo')
                ON CONFLICT (id) DO NOTHING
                """,
                (tenant_a, tenant_b),
            )
            cursor.execute(
                """
                INSERT INTO subscription_plans (
                    id, name, display_name_ar, price, duration_days,
                    is_ai_enabled, ai_daily_limit, is_default, is_active, created_at
                )
                VALUES (
                    %s, 'rls-contract-plan', 'RLS Contract', 1, 30,
                    FALSE, 0, FALSE, TRUE, NOW()
                )
                ON CONFLICT (id) DO NOTHING
                """,
                (plan_id,),
            )
            cursor.execute(
                """
                INSERT INTO subscription_payments (
                    id, tenant_id, plan_id, amount, payment_method, payment_date
                )
                VALUES
                    (%s, %s, %s, 10, 'ci', NOW()),
                    (%s, %s, %s, 20, 'ci', NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                (payment_a, tenant_a, plan_id, payment_b, tenant_b, plan_id),
            )
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('rls.bypass_rls', 'false', false)"
            )
            cursor.execute(
                "SELECT set_config('rls.tenant_id', %s, false)",
                (str(tenant_a),),
            )
            cursor.execute(
                "SELECT id FROM subscription_payments "
                "WHERE id IN (%s, %s) ORDER BY id",
                (payment_a, payment_b),
            )
            assert [row[0] for row in cursor.fetchall()] == [payment_a]

            cursor.execute(
                "UPDATE subscription_payments SET amount = amount + 1 WHERE id = %s",
                (payment_b,),
            )
            assert cursor.rowcount == 0

            # WITH CHECK must reject a tenant-A session trying to create a
            # tenant-B row, not merely hide it on later SELECTs.
            with pytest.raises(psycopg2.Error) as exc_info:
                cursor.execute(
                    """
                    INSERT INTO subscription_payments (
                        id, tenant_id, plan_id, amount, payment_method, payment_date
                    )
                    VALUES (%s, %s, %s, 30, 'ci-cross-tenant', NOW())
                    """,
                    (993662, tenant_b, plan_id),
                )
            assert exc_info.value.pgcode == "42501"
        connection.rollback()

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('rls.bypass_rls', 'false', false)"
            )
            cursor.execute(
                "SELECT set_config('rls.tenant_id', %s, false)",
                (str(tenant_b),),
            )
            cursor.execute(
                "SELECT id FROM subscription_payments "
                "WHERE id IN (%s, %s) ORDER BY id",
                (payment_a, payment_b),
            )
            assert [row[0] for row in cursor.fetchall()] == [payment_b]
        connection.rollback()

    yield


@pytest_asyncio.fixture(autouse=True)
async def isolate_async_engine_pool_between_tests():
    """Avoid reusing asyncpg connections across pytest event loops."""
    yield
    await async_engine.dispose()
