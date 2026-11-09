"""Explicit catalog setup preserves all legacy contracts and requires a fresh preview."""

import pytest
from types import SimpleNamespace
from decimal import Decimal
from datetime import datetime
from backend import models
from backend.auth import create_access_token


@pytest.fixture
def catalog_case(db_session):
    legacy = models.SubscriptionPlan(
        name="pro",
        display_name_ar="Synthetic legacy",
        price=1000,
        max_users=5,
        is_ai_enabled=False,
        ai_daily_limit=0,
        is_active=True,
        features="old metadata",
    )
    db_session.add(legacy)
    db_session.flush()
    tenant = models.Tenant(
        name="Synthetic existing",
        plan_id=legacy.id,
        plan="pro",
        subscription_status="active",
        subscription_end_date=datetime(2027, 1, 31),
    )
    admin = models.User(
        username="catalog_setup_admin",
        hashed_password="synthetic",
        role="super_admin",
        is_active=True,
    )
    db_session.add_all([tenant, admin])
    db_session.commit()
    return SimpleNamespace(
        legacy=legacy,
        tenant=tenant,
        admin=admin,
        headers={
            "Authorization": "Bearer "
            + create_access_token(
                data={"sub": admin.username, "role": admin.role, "tenant_id": None}
            )
        },
    )


def preview(client, case):
    response = client.get(
        "/api/v1/admin/subscriptions/catalog-setup-preview", headers=case.headers
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_preview_then_apply_preserves_existing_contract(
    client, db_session, catalog_case
):
    case = catalog_case
    before = case.tenant.subscription_end_date
    data = preview(client, case)
    assert {p["name"] for p in data["create_plans"]} == {
        "essential",
        "professional",
        "business",
    }
    assert db_session.query(models.SubscriptionPlan).count() == 1
    response = client.post(
        "/api/v1/admin/subscriptions/catalog-setup",
        headers=case.headers,
        json={
            "expected_snapshot": data["snapshot"],
            "reason": "Owner approved catalog setup",
        },
    )
    assert response.status_code == 200, response.text
    db_session.expire_all()
    assert db_session.query(models.SubscriptionPlan).count() == 4
    assert db_session.get(models.SubscriptionPlan, case.legacy.id).price == Decimal(
        "1000.00"
    )
    tenant = db_session.get(models.Tenant, case.tenant.id)
    assert (tenant.plan_id, tenant.plan, tenant.subscription_end_date) == (
        case.legacy.id,
        "pro",
        before,
    )
    settings = {r.key: r.value for r in db_session.query(models.SystemSetting).all()}
    assert settings["system_trial_plan_name"] == "professional"
    assert settings["system_trial_duration_days"] == "14"
    assert (
        db_session.query(models.AuditLog)
        .filter_by(action="COMMERCIAL_CATALOG_SETUP")
        .count()
        == 1
    )
    replay = client.post(
        "/api/v1/admin/subscriptions/catalog-setup",
        headers=case.headers,
        json={"expected_snapshot": data["snapshot"], "reason": "Same stale approval"},
    )
    assert replay.status_code == 409
    assert db_session.query(models.SubscriptionPlan).count() == 4


def test_existing_conflicting_professional_requires_explicit_review(
    client, db_session, catalog_case
):
    db_session.add(
        models.SubscriptionPlan(
            name="professional",
            display_name_ar="Custom saved contract",
            price=777,
            is_active=True,
        )
    )
    db_session.commit()
    data = preview(client, catalog_case)
    assert data["conflicts"]
    response = client.post(
        "/api/v1/admin/subscriptions/catalog-setup",
        headers=catalog_case.headers,
        json={
            "expected_snapshot": data["snapshot"],
            "reason": "Must preserve custom saved price",
        },
    )
    assert response.status_code == 409
    assert db_session.query(models.SubscriptionPlan).count() == 2


def test_setup_is_super_admin_only(client, db_session, catalog_case):
    catalog_case.admin.role = "doctor"
    catalog_case.admin.tenant_id = catalog_case.tenant.id
    db_session.commit()
    for path in ("catalog-setup-preview", "catalog-setup"):
        response = (client.get if path.endswith("preview") else client.post)(
            "/api/v1/admin/subscriptions/" + path, headers=catalog_case.headers
        )
        assert response.status_code == 403, response.text


def test_matching_object_features_preserve_explicit_false_metadata(
    client, db_session, catalog_case
):
    import json
    from backend.services.subscription_service import SubscriptionService

    spec = next(
        s
        for s in SubscriptionService.get_launch_catalog_template()
        if s["name"] == "professional"
    )
    features = {key: True for key in json.loads(spec["features"])}
    features["patient_portal"] = False
    spec = {**spec, "features": json.dumps(features)}
    plan = models.SubscriptionPlan(**spec, is_active=True)
    db_session.add(plan)
    db_session.commit()
    data = preview(client, catalog_case)
    assert data["conflicts"] == []
    assert {p["name"] for p in data["create_plans"]} == {"essential", "business"}
