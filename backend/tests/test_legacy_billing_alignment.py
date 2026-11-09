"""Approved catalog conversion is atomic, exact-cohort and replay safe on PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
import json
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from backend import models
from backend.services.legacy_billing_alignment import (
    APPROVAL_KEY,
    APPLIED_KEY,
    INSTALLATION_KEY,
    align_legacy_billing_terms,
)
from backend.tests import test_promotion_ai_policy as fixtures

policy_database = fixtures.policy_database


@pytest.fixture
def approved_catalog(policy_database):
    case = policy_database
    with Session(case.engine) as db:
        legacy = db.scalar(select(models.SubscriptionPlan))
        legacy.name, legacy.duration_days = "vib", 3650
        monthly = []
        for name in ("essential", "professional", "business"):
            plan = models.SubscriptionPlan(
                name=name,
                display_name_ar="Synthetic",
                price=400,
                duration_days=30,
                billing_cycle_unit="month",
                is_active=True,
            )
            db.add(plan)
            db.flush()
            monthly.append(dict(id=plan.id, name=name, duration_days=30))
        installation_id = str(uuid4())
        payload = dict(
            version=1,
            environment="production",
            installation_id=installation_id,
            legacy=[dict(id=legacy.id, name="vib", duration_days=3650)],
            monthly=monthly,
        )
        db.add(models.SystemSetting(key=INSTALLATION_KEY, value=installation_id))
        db.add(models.SystemSetting(key=APPROVAL_KEY, value=json.dumps(payload)))
        db.commit()
    return case


def snapshot(case):
    with Session(case.engine) as db:
        return {
            "plans": [
                dict(
                    id=p.id,
                    name=p.name,
                    duration=p.duration_days,
                    price=str(p.price),
                    seats=p.max_users,
                    active=p.is_active,
                    unit=p.billing_cycle_unit,
                    revision=p.policy_revision,
                )
                for p in db.scalars(
                    select(models.SubscriptionPlan).order_by(models.SubscriptionPlan.id)
                )
            ],
            "period": db.get(models.Tenant, case.tenant_id).subscription_end_date,
            "audits": db.query(models.AuditLog)
            .filter_by(action="LEGACY_BILLING_TERMS_ALIGNED")
            .count(),
            "marker": db.get(models.SystemSetting, APPLIED_KEY).value
            if db.get(models.SystemSetting, APPLIED_KEY)
            else None,
        }


def test_exact_approved_terms_align_once_without_changing_contracts(approved_catalog):
    case = approved_catalog
    before = snapshot(case)
    assert align_legacy_billing_terms(case.engine, required=True) is True
    after = snapshot(case)
    expected = {**before["plans"][0], "unit": "day", "revision": 2}
    assert after["plans"] == [expected, *before["plans"][1:]]
    assert after["period"] == before["period"]
    assert after["audits"] == 1 and after["marker"]
    assert align_legacy_billing_terms(case.engine, required=True) is False
    assert snapshot(case) == after
    with Session(case.engine) as db:
        plan = db.get(models.SubscriptionPlan, expected["id"])
        plan.billing_cycle_unit = "year"  # A later explicit administrator decision.
        db.commit()
    assert align_legacy_billing_terms(case.engine, required=True) is False
    assert snapshot(case)["plans"][0]["unit"] == "year"


@pytest.mark.parametrize(
    "drift",
    [
        "name",
        "duration_days",
        "unit",
        "extra",
        "missing",
        "installation",
        "duplicate",
        "malformed",
    ],
)
def test_catalog_drift_aborts_before_any_update(approved_catalog, drift):
    case = approved_catalog
    with Session(case.engine) as db:
        row = db.scalar(
            select(models.SubscriptionPlan).where(models.SubscriptionPlan.name == "vib")
        )
        if drift == "name":
            row.name = "unexpected"
        elif drift == "duration_days":
            row.duration_days = 30
        elif drift == "unit":
            row.billing_cycle_unit = "year"
        elif drift == "extra":
            db.add(
                models.SubscriptionPlan(
                    name="unreviewed",
                    display_name_ar="Synthetic",
                    price=100,
                    duration_days=30,
                )
            )
        elif drift == "missing":
            db.delete(
                db.scalar(
                    select(models.SubscriptionPlan).where(
                        models.SubscriptionPlan.name == "business"
                    )
                )
            )
        elif drift == "installation":
            db.get(models.SystemSetting, INSTALLATION_KEY).value = str(uuid4())
        elif drift == "malformed":
            db.get(models.SystemSetting, APPROVAL_KEY).value = "not-json"
        elif drift == "duplicate":
            approval = db.get(models.SystemSetting, APPROVAL_KEY)
            payload = json.loads(approval.value)
            payload["legacy"].append(payload["legacy"][0])
            approval.value = json.dumps(payload)
        db.commit()
    before = snapshot(case)
    with pytest.raises(ValueError):
        align_legacy_billing_terms(case.engine, required=True)
    assert snapshot(case) == before


def test_audit_failure_rolls_back_term_updates_and_marker(approved_catalog):
    case = approved_catalog
    before = snapshot(case)

    def fail_audit(conn, cursor, statement, parameters, context, executemany):
        if (
            statement.lstrip().upper().startswith("INSERT INTO")
            and "audit_logs" in statement
        ):
            raise RuntimeError("Synthetic audit write failure")

    event.listen(case.engine, "before_cursor_execute", fail_audit)
    try:
        with pytest.raises(RuntimeError, match="Synthetic audit"):
            align_legacy_billing_terms(case.engine)
    finally:
        event.remove(case.engine, "before_cursor_execute", fail_audit)
    assert snapshot(case) == before


def test_concurrent_starts_apply_one_audit_and_revision(approved_catalog):
    case = approved_catalog
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: align_legacy_billing_terms(case.engine), range(2))
        )
    assert sorted(results) == [False, True]
    state = snapshot(case)
    assert state["audits"] == 1 and state["plans"][0]["revision"] == 2


def test_missing_approval_rejects_legacy_but_allows_fresh_launch_restart(
    policy_database,
):
    case = policy_database
    # Fixture has only a launch Professional plan, matching a freshly seeded app.
    assert align_legacy_billing_terms(case.engine, required=True) is False
    with Session(case.engine) as db:
        db.add(
            models.SubscriptionPlan(
                name="legacy", display_name_ar="Synthetic", price=500, duration_days=30
            )
        )
        db.commit()
    before = snapshot(case)
    with pytest.raises(ValueError, match="approval is required"):
        align_legacy_billing_terms(case.engine, required=True)
    assert snapshot(case) == before
