import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from backend import models
from backend.database import Base
from backend.ai.analytics.service import AIAnalyticsService


@pytest.mark.asyncio
async def test_ai_analytics_get_stats(async_db_session, async_engine_fixture):
    # Ensure tables are created in the async test database
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure Tenant exists
    stmt_tenant = select(models.Tenant).where(models.Tenant.id == 1)
    res_tenant = await async_db_session.execute(stmt_tenant)
    tenant = res_tenant.scalars().first()
    if not tenant:
        tenant = models.Tenant(id=1, name="Test Clinic", plan="Pro")
        async_db_session.add(tenant)
        await async_db_session.commit()

    # Create dummy User for AIUsageLog if not exists
    stmt_user = select(models.User).where(models.User.id == 101)
    res_user = await async_db_session.execute(stmt_user)
    user = res_user.scalars().first()
    if not user:
        user = models.User(
            id=101,
            username="test_ai_user",
            email="test_ai_user@example.com",
            hashed_password="hashed_password",
            role="doctor",
            tenant_id=1,
        )
        async_db_session.add(user)
        await async_db_session.commit()

    # Create dummy AIUsageLog entries
    log1 = models.AIUsageLog(
        trace_id="trace-1",
        tenant_id=1,
        user_id=101,
        intent="patient_summary",
        tool="get_patient_file",
        model="llama-3-8b",
        input_text="hello",
        output_text="hi",
        status="SUCCESS",
        execution_time_ms=120,
        username="test_ai_user",
        created_at=datetime.now(timezone.utc),
    )
    log2 = models.AIUsageLog(
        trace_id="trace-2",
        tenant_id=1,
        user_id=101,
        intent="patient_summary",
        tool="get_patient_file",
        model="llama-3-8b",
        input_text="hello",
        output_text="hi",
        status="FAILURE",
        execution_time_ms=80,
        username="test_ai_user",
        created_at=datetime.now(timezone.utc),
    )
    async_db_session.add_all([log1, log2])
    await async_db_session.commit()

    # Call get_stats
    stats = await AIAnalyticsService.get_stats(async_db_session, "month", 1)
    assert stats is not None
    assert stats["total_requests"] >= 2
    assert "success_rate" in stats
    assert len(stats["tool_usage"]) > 0
    # Find tool usage for get_patient_file
    tool_uses = [t for t in stats["tool_usage"] if t["name"] == "get_patient_file"]
    assert len(tool_uses) > 0
    assert tool_uses[0]["value"] >= 2
    
    # Find top user
    user_stats = [u for u in stats["top_users"] if u["name"] == "test_ai_user"]
    assert len(user_stats) > 0
    assert user_stats[0]["count"] >= 2
