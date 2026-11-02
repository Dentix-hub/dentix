"""Released sessions are enabled for existing and future clinics on deployment."""

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend import models
from backend.services.feature_service import FeatureFlagService
from backend.tests.test_preflight_postgres_contract import (
    _create_database,
    _drop_database,
    _postgres_base_url,
)

NATIVE = "clinical_vnext_native_writes"


@pytest.fixture(params=["sqlite", "postgresql"])
def activation_database(request, tmp_path):
    if request.param == "postgresql":
        base_url = _postgres_base_url()
        name, url = _create_database(base_url)
    else:
        url = f"sqlite:///{tmp_path / 'activation.db'}"
    engine = sa.create_engine(url)
    try:
        models.Base.metadata.create_all(engine)
        config = Config("backend/alembic.ini")
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        command.stamp(config, "c2d3e4f5a6b7")
        yield engine, config
    finally:
        engine.dispose()
        if request.param == "postgresql":
            _drop_database(base_url, name)


@pytest.mark.parametrize("existing_flag", [False, True])
@pytest.mark.asyncio
async def test_upgrade_enables_all_clinics_and_preserves_other_data(activation_database, existing_flag):
    engine, config = activation_database
    flags = models.FeatureFlag.__table__
    overrides = models.TenantFeature.__table__
    with engine.begin() as conn:
        conn.execute(models.Tenant.__table__.insert(), [
            {"id": 1, "name": "Synthetic Alpha"},
            {"id": 2, "name": "Synthetic Beta"},
            {"id": 3, "name": "Synthetic Gamma"},
        ])
        conn.execute(flags.insert(), {"key": "clinical_vnext_finance_read", "is_global_enabled": False, "rollout_percentage": 0})
        if existing_flag:
            conn.execute(flags.insert(), {"key": NATIVE, "description": "Existing rollout", "is_global_enabled": False, "rollout_percentage": 5})
            conn.execute(overrides.insert(), [
                {"tenant_id": 1, "feature_key": NATIVE, "is_enabled": False},
                {"tenant_id": 2, "feature_key": NATIVE, "is_enabled": True},
            ])
        conn.execute(overrides.insert(), {"tenant_id": 1, "feature_key": "clinical_vnext_finance_read", "is_enabled": False})
        conn.execute(models.Patient.__table__.insert(), {"id": 1, "tenant_id": 1, "name": "Synthetic patient"})
        conn.execute(models.CareSession.__table__.insert(), {"id": 1, "tenant_id": 1, "patient_id": 1, "notes": "Existing clinical narrative", "status": "completed"})

    command.upgrade(config, "head")

    with engine.begin() as conn:
        flag = conn.execute(sa.select(flags).where(flags.c.key == NATIVE)).mappings().one()
        assert flag["is_global_enabled"] is True
        assert flag["rollout_percentage"] == 100
        assert conn.execute(sa.select(overrides.c.is_enabled).where(overrides.c.feature_key == NATIVE)).scalars().all() == ([True, True] if existing_flag else [])
        assert conn.scalar(sa.select(flags.c.is_global_enabled).where(flags.c.key == "clinical_vnext_finance_read")) is False
        assert conn.scalar(sa.select(overrides.c.is_enabled).where(overrides.c.feature_key == "clinical_vnext_finance_read", overrides.c.tenant_id == 1)) is False
        assert conn.scalar(sa.select(models.CareSession.notes).where(models.CareSession.id == 1)) == "Existing clinical narrative"
        # A later-created clinic inherits the global policy without a new override.
        conn.execute(models.Tenant.__table__.insert(), {"id": 4, "name": "Synthetic future clinic"})
        assert conn.scalar(sa.select(sa.func.count()).select_from(overrides).where(overrides.c.tenant_id == 4)) == 0
    driver = "postgresql+asyncpg" if engine.dialect.name == "postgresql" else "sqlite+aiosqlite"
    async_engine = create_async_engine(engine.url.set(drivername=driver))
    try:
        async with AsyncSession(async_engine) as db:
            for tenant_id in (1, 2, 3, 4):
                assert await FeatureFlagService.is_feature_enabled(db, NATIVE, tenant_id) is True
                assert await FeatureFlagService.is_feature_enabled(db, "clinical_vnext_finance_read", tenant_id) is False
    finally:
        await async_engine.dispose()
    with engine.begin() as conn:
        # Later deliberate opt-outs must survive normal restarts/up-to-date deploys.
        conn.execute(overrides.insert(), {"tenant_id": 3, "feature_key": NATIVE, "is_enabled": False})
    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert conn.scalar(sa.select(overrides.c.is_enabled).where(overrides.c.tenant_id == 3, overrides.c.feature_key == NATIVE)) is False
    command.downgrade(config, "c2d3e4f5a6b7")
    with engine.connect() as conn:
        assert conn.scalar(sa.select(overrides.c.is_enabled).where(overrides.c.tenant_id == 3, overrides.c.feature_key == NATIVE)) is False
        assert conn.scalar(sa.select(flags.c.is_global_enabled).where(flags.c.key == NATIVE)) is True
