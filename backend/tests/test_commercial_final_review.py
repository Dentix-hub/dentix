"""Final-plan policy integration regressions, through actual stored policy and HTTP."""

from datetime import datetime, timedelta
import pytest
from backend import models
from backend.auth import create_access_token
from backend.services.entitlement_service import EntitlementService
from backend.tests import test_commercial_release_hardening as fixtures

sample = fixtures.sample
enforced = fixtures.enforced


def headers(sample):
    return {
        "Authorization": "Bearer "
        + create_access_token(
            data={
                "sub": sample.user.username,
                "role": sample.user.role,
                "tenant_id": sample.tenant.id,
            }
        )
    }


@pytest.mark.asyncio
async def test_persisted_allow_deny_and_expiry_load_as_actual_values(
    db_session, async_db_session, sample
):
    db_session.add_all(
        [
            models.CommercialTenantOverride(
                tenant_id=sample.tenant.id,
                capability_key="clinical",
                override_value="deny",
                reason="Synthetic denial",
            ),
            models.CommercialTenantOverride(
                tenant_id=sample.tenant.id,
                capability_key="inventory",
                override_value="allow",
                reason="Synthetic allowance",
            ),
            models.CommercialTenantOverride(
                tenant_id=sample.tenant.id,
                capability_key="billing",
                override_value="deny",
                reason="Expired synthetic override",
                expires_at=datetime.utcnow() - timedelta(days=1),
            ),
        ]
    )
    db_session.commit()
    _, overrides = await EntitlementService.async_resolve_restrictions_and_overrides(
        async_db_session, sample.tenant.id
    )
    assert overrides == {"clinical": False, "inventory": True}


def test_persisted_clinical_deny_blocks_direct_patient_api(client, db_session, sample):
    db_session.add(
        models.CommercialTenantOverride(
            tenant_id=sample.tenant.id,
            capability_key="clinical",
            override_value="deny",
            reason="Synthetic policy denial",
        )
    )
    db_session.commit()
    before = db_session.query(models.Patient).count()
    response = client.post(
        "/api/v1/patients",
        json={"name": "Synthetic denied patient", "phone": "01000000000"},
        headers=headers(sample),
    )
    assert response.status_code == 403, response.text
    assert db_session.query(models.Patient).count() == before


@pytest.mark.parametrize("mode", ["off", "observe", "enforce"])
def test_emergency_stops_direct_writes_but_preserves_history(
    client, db_session, sample, monkeypatch, mode
):
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", mode)
    patient = models.Patient(
        name="Synthetic existing history",
        phone="01000000000",
        tenant_id=sample.tenant.id,
    )
    db_session.add(patient)
    db_session.add(
        models.SystemSetting(key="emergency_restriction_clinical", value="true")
    )
    db_session.commit()
    response = client.post(
        "/api/v1/patients",
        json={"name": "Synthetic emergency denied", "phone": "01000000000"},
        headers=headers(sample),
    )
    assert response.status_code == 403, response.text
    assert db_session.query(models.Patient).count() == 1
    history = client.get(f"/api/v1/patients/{patient.id}", headers=headers(sample))
    assert history.status_code == 200, history.text


@pytest.mark.parametrize("mode", ["off", "observe", "enforce"])
def test_evaluation_does_not_mask_emergency_decisions(sample, mode):
    result = EntitlementService.evaluate_tenant_entitlements(
        sample.tenant,
        override_mode=mode,
        emergency_restrictions={
            "clinical",
            "billing",
            "inventory",
            "laboratories",
            "tenant_backups",
        },
    )
    assert result.can_read_clinical is True
    assert result.can_write_clinical is False
    assert result.can_write_billable is False
    assert result.can_create_appointments is False
    assert result.can_manage_inventory is False
    assert result.can_manage_laboratories is False
    assert result.can_manage_backups is False


@pytest.mark.parametrize("case", ["missing_plan", "rollout_denied"])
def test_enforced_write_flags_follow_canonical_decision(sample, case):
    if case == "missing_plan":
        sample.tenant.plan_id = None
        sample.tenant.subscription_plan = None
    result = EntitlementService.evaluate_tenant_entitlements(
        sample.tenant,
        override_mode="enforce",
        rollout_resolver=(lambda *_: False) if case == "rollout_denied" else None,
    )
    assert result.can_read_clinical is True
    assert result.can_write_clinical is False
    # Clinical rollout does not withdraw the independent billing capability.
    assert result.can_write_billable is (case == "rollout_denied")


def test_operational_shadow_flags_follow_actual_decisions(sample):
    sample.tenant.subscription_status = "expired_read_only"
    result = EntitlementService.evaluate_tenant_entitlements(
        sample.tenant, override_mode="observe"
    )
    assert result.can_manage_inventory is True
    assert result.can_manage_laboratories is True
    assert result.can_manage_backups is True


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["system_settings", "commercial_tenant_overrides"])
async def test_policy_lookup_failure_denies_new_use_without_blocking_history(
    async_db_session, sample, monkeypatch, table
):
    execute = async_db_session.execute

    async def failed_policy(statement, *args, **kwargs):
        if table in str(statement):
            raise RuntimeError("Synthetic policy store failure")
        return await execute(statement, *args, **kwargs)

    monkeypatch.setattr(async_db_session, "execute", failed_policy)
    (
        restrictions,
        overrides,
    ) = await EntitlementService.async_resolve_restrictions_and_overrides(
        async_db_session, sample.tenant.id
    )
    result = EntitlementService.evaluate_tenant_entitlements(
        sample.tenant,
        override_mode="off",
        emergency_restrictions=restrictions,
        commercial_overrides=overrides,
    )
    assert not result.can_write_clinical
    assert not result.can_write_billable
    assert result.can_read_clinical


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["system_settings", "commercial_tenant_overrides"])
async def test_postgres_policy_failure_does_not_poison_history_transaction(
    pg_case, table
):
    from sqlalchemy import event, select, func
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from backend.tests.test_commercial_plan_completion import URL

    engine = create_async_engine(URL.replace("postgresql://", "postgresql+asyncpg://"))
    fired = False

    def inject_failure(conn, cursor, statement, parameters, context, executemany):
        nonlocal fired
        if not fired and f"FROM {table}" in statement:
            fired = True
            cursor.execute("SELECT CAST('synthetic-policy-failure' AS integer)")

    event.listen(engine.sync_engine, "before_cursor_execute", inject_failure)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            (
                restrictions,
                _,
            ) = await EntitlementService.async_resolve_restrictions_and_overrides(
                db, pg_case.tenant.id
            )
            assert fired
            assert "clinical" in restrictions
            count = await db.scalar(
                select(func.count(models.User.id)).where(
                    models.User.tenant_id == pg_case.tenant.id
                )
            )
            assert count == 3
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", inject_failure)
        await engine.dispose()


from backend.tests import test_commercial_plan_completion as completion_fixtures

pg_case = completion_fixtures.pg_case
