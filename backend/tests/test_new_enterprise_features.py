import pytest
from sqlalchemy import select
from backend.models import User, FeatureFlag, TenantFeature, Tenant
from backend.services.security_service import SecurityService
from backend.services.feature_service import FeatureFlagService
from backend import schemas
from backend.database import Base


@pytest.fixture(autouse=True)
async def setup_tables(async_engine_fixture):
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.anyio
async def test_security_service(async_db_session):
    # 1. Test Block IP
    test_ip = "192.168.1.99"
    await SecurityService.block_ip(async_db_session, test_ip, "Test Block", "admin", minutes=1)
    
    blocked = await SecurityService.check_ip_blocked(async_db_session, test_ip)
    assert blocked is not None
    
    await SecurityService.unblock_ip(async_db_session, test_ip)
    blocked = await SecurityService.check_ip_blocked(async_db_session, test_ip)
    assert blocked is None

    # 2. Test Lockout
    existing_user_stmt = select(User).where(User.username == "security_test_user")
    existing_user = (await async_db_session.execute(existing_user_stmt)).scalar_one_or_none()
    if existing_user:
        await async_db_session.delete(existing_user)
        await async_db_session.commit()

    temp_user = User(
        username="security_test_user", 
        email="sectest@example.com", 
        hashed_password="pw"
    )
    async_db_session.add(temp_user)
    await async_db_session.commit()

    for i in range(5):
        await SecurityService.record_login_attempt(
            async_db_session, "127.0.0.1", temp_user.username, False, temp_user
        )

    await async_db_session.refresh(temp_user)
    assert temp_user.failed_login_attempts == 5
    assert SecurityService.is_account_locked(temp_user) is True

    # Cleanup
    await async_db_session.delete(temp_user)
    await async_db_session.commit()


@pytest.mark.anyio
async def test_feature_flags(async_db_session):
    key = "test_feature_ai"

    # Cleanup first
    existing_stmt = select(FeatureFlag).where(FeatureFlag.key == key)
    existing = (await async_db_session.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        await async_db_session.delete(existing)
        await async_db_session.commit()

    flag_data = schemas.FeatureFlagCreate(
        key=key,
        description="Test AI",
        is_global_enabled=False,
        rollout_percentage=0,
    )
    await FeatureFlagService.create_flag(async_db_session, flag_data)

    # Check Default (Should be False)
    is_enabled = await FeatureFlagService.is_feature_enabled(async_db_session, key)
    assert is_enabled is False

    # Enable Global
    await FeatureFlagService.update_flag(async_db_session, key, {"is_global_enabled": True})
    is_enabled = await FeatureFlagService.is_feature_enabled(async_db_session, key)
    assert is_enabled is True

    # Test Tenant Override
    tenant_stmt = select(Tenant)
    tenant = (await async_db_session.execute(tenant_stmt)).scalars().first()
    if tenant:
        t_id = tenant.id
        await FeatureFlagService.set_tenant_override(async_db_session, t_id, key, False)
        is_enabled = await FeatureFlagService.is_feature_enabled(async_db_session, key, t_id)
        assert is_enabled is False

        # Clean override
        delete_override_stmt = select(TenantFeature).where(
            TenantFeature.tenant_id == t_id,
            TenantFeature.feature_key == key
        )
        override = (await async_db_session.execute(delete_override_stmt)).scalar_one_or_none()
        if override:
            await async_db_session.delete(override)
            await async_db_session.commit()

    # Cleanup flag
    flag_stmt = select(FeatureFlag).where(FeatureFlag.key == key)
    flag = (await async_db_session.execute(flag_stmt)).scalar_one_or_none()
    if flag:
        await async_db_session.delete(flag)
        await async_db_session.commit()
