"""Regression tests for Google Drive disconnect scoping (CRITICAL-03).

A failing tenant backup must clear ONLY that tenant's refresh token.
The global super-admin token must survive tenant backup failures and may
only be cleared by an explicit global (tenant_id=None) backup.
"""

import pytest
from sqlalchemy import select

from backend import models
from backend.services.backup_service import disconnect_drive_credentials
from backend.services.secret_service import GOOGLE_SUPER_ADMIN_TOKEN_KEY


@pytest.fixture
def clinic_with_token(db_session, test_tenant):
    test_tenant.google_refresh_token = "tenant-refresh-token-OLD"
    db_session.commit()
    db_session.refresh(test_tenant)
    return test_tenant


@pytest.fixture
def global_token_setting(db_session):
    setting = models.SystemSetting(
        key=GOOGLE_SUPER_ADMIN_TOKEN_KEY, value="global-super-admin-token"
    )
    db_session.add(setting)
    db_session.commit()
    db_session.refresh(setting)
    return setting


@pytest.mark.asyncio
async def test_tenant_failure_clears_only_tenant_token(
    async_db_session, clinic_with_token, global_token_setting
):
    session = async_db_session
    await disconnect_drive_credentials(session, "tenant-refresh-token-OLD", clinic_with_token.id)
    await session.commit()

    refreshed_tenant = (
        (await session.execute(
            select(models.Tenant).filter(models.Tenant.id == clinic_with_token.id)
        ))
        .scalars()
        .first()
    )
    assert refreshed_tenant.google_refresh_token is None

    # Global super-admin token untouched by the tenant failure.
    setting = (
        (await session.execute(
            select(models.SystemSetting).filter(
                models.SystemSetting.key == GOOGLE_SUPER_ADMIN_TOKEN_KEY
            )
        ))
        .scalars()
        .first()
    )
    assert setting is not None
    assert setting.value == "global-super-admin-token"


@pytest.mark.asyncio
async def test_global_failure_clears_global_token_only(
    async_db_session, clinic_with_token, global_token_setting
):
    session = async_db_session
    await disconnect_drive_credentials(session, "global-super-admin-token", None)
    await session.commit()

    setting = (
        (await session.execute(
            select(models.SystemSetting).filter(
                models.SystemSetting.key == GOOGLE_SUPER_ADMIN_TOKEN_KEY
            )
        ))
        .scalars()
        .first()
    )
    assert setting is None

    # Tenant token untouched by a global failure path.
    refreshed_tenant = (
        (await session.execute(
            select(models.Tenant).filter(models.Tenant.id == clinic_with_token.id)
        ))
        .scalars()
        .first()
    )
    assert refreshed_tenant.google_refresh_token == "tenant-refresh-token-OLD"


@pytest.mark.asyncio
async def test_reconnected_tenant_keeps_new_token(
    async_db_session, clinic_with_token, global_token_setting
):
    """If the clinic reconnected during the failed backup, keep the new token."""
    session = async_db_session
    await disconnect_drive_credentials(session, "stale-token-from-old-run", clinic_with_token.id)
    await session.commit()

    refreshed_tenant = (
        (await session.execute(
            select(models.Tenant).filter(models.Tenant.id == clinic_with_token.id)
        ))
        .scalars()
        .first()
    )
    assert refreshed_tenant.google_refresh_token == "tenant-refresh-token-OLD"


@pytest.mark.asyncio
async def test_missing_refresh_token_is_noop(
    async_db_session, clinic_with_token, global_token_setting
):
    session = async_db_session
    await disconnect_drive_credentials(session, None, None)
    await disconnect_drive_credentials(session, "", clinic_with_token.id)

    setting = (
        (await session.execute(
            select(models.SystemSetting).filter(
                models.SystemSetting.key == GOOGLE_SUPER_ADMIN_TOKEN_KEY
            )
        ))
        .scalars()
        .first()
    )
    assert setting is not None
