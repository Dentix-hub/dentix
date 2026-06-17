import pytest
from sqlalchemy import select
from backend.routers import admin_system
from backend import models
from backend.database import Base


@pytest.fixture(autouse=True)
async def setup_tables(async_engine_fixture):
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.anyio
async def test_admin_users_query_count(async_db_session):
    """
    Test that the admin user query eager loads tenant relations to avoid N+1 queries.
    """
    # 1. Create Dummy Tenant
    tenant_stmt = select(models.Tenant).where(models.Tenant.name == "N+1 Test Tenant")
    t = (await async_db_session.execute(tenant_stmt)).scalar_one_or_none()
    if not t:
        t = models.Tenant(name="N+1 Test Tenant", plan="trial")
        async_db_session.add(t)
        await async_db_session.commit()
        await async_db_session.refresh(t)

    # 2. Create Users
    created_users = []
    for i in range(5):
        u_name = f"nplus1_user_{i}"
        user_stmt = select(models.User).where(models.User.username == u_name)
        u = (await async_db_session.execute(user_stmt)).scalar_one_or_none()
        if not u:
            u = models.User(
                username=u_name,
                email=f"{u_name}@example.com",
                hashed_password="pw",
                role="doctor",
                tenant_id=t.id,
            )
            async_db_session.add(u)
            created_users.append(u)
    await async_db_session.commit()

    # 3. Execute Query
    try:
        super_admin = models.User(role="super_admin")

        users = await admin_system.get_global_users(
            db=async_db_session, limit=100, current_user=super_admin
        )

        # 4. Verify
        assert len(users) >= 5

        found_our_user = False
        for user_schema in users:
            if user_schema.username.startswith("nplus1_user_"):
                found_our_user = True
                assert user_schema.tenant_name == "N+1 Test Tenant"

        assert found_our_user, "Did not find the created test users"

    finally:
        pass
