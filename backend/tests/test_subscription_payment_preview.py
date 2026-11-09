"""Receipt preview must use the actual period grant without writing records."""

from datetime import datetime
import pytest
from sqlalchemy import event

from backend import models
from backend.tests import test_commercial_plan_completion as fixtures

pg_case = fixtures.pg_case
pg_client = fixtures.pg_client
headers = fixtures.headers


@pytest.mark.parametrize(
    "unit,days,expected",
    [
        ("day", 3650, datetime(2036, 1, 29, 10)),
        ("day", 30, datetime(2026, 3, 2, 10)),
        ("month", 30, datetime(2026, 2, 28, 10)),
        ("year", 30, datetime(2027, 1, 31, 10)),
    ],
)
def test_payment_honors_stored_plan_term_and_preserves_existing_receipts(
    pg_case, pg_client, monkeypatch, unit, days, expected
):
    from backend.services.subscription_service import SubscriptionService

    # 3650 UTC days = ten 365-day years; Jan 31, 2026 -> Jan 29, 2036
    # after the two intervening leap days. 30 days -> Mar 2; month -> Feb 28.
    monkeypatch.setattr(
        SubscriptionService, "_utc_now_naive", lambda: datetime(2026, 1, 1, 10)
    )
    plan = models.SubscriptionPlan(
        name=f"synthetic_{pg_case.tenant.id}_{unit}_{days}",
        display_name_ar="Synthetic",
        price=400,
        duration_days=days,
        billing_cycle_unit=unit,
        max_users=5,
        is_active=True,
    )
    pg_case.db.add(plan)
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    tenant.plan_id = pg_case.plans["professional"].id
    tenant.subscription_end_date = datetime(2026, 1, 31, 10)
    tenant.billing_day_anchor = 31
    historical = models.SubscriptionPayment(
        tenant_id=tenant.id,
        plan_id=tenant.plan_id,
        amount=400,
        payment_method="cash",
        payment_date=datetime(2025, 12, 1, 10),
    )
    pg_case.db.add(historical)
    pg_case.db.commit()
    old_receipt_id = historical.id
    payload = dict(
        tenant_id=tenant.id, plan_id=plan.id, amount=400, payment_method="cash"
    )
    preview = pg_client.post(
        "/api/v1/admin/subscriptions/payments/preview",
        json=payload,
        headers=headers(pg_case),
    )
    assert preview.status_code == 200, preview.text
    quoted = preview.json()["data"]
    assert quoted["after"]["subscription_end_date"] == expected.isoformat()
    pg_case.db.expire_all()
    assert pg_case.db.get(models.Tenant, tenant.id).subscription_end_date == datetime(
        2026, 1, 31, 10
    )
    payload.update(
        preview_marker=quoted["preview_marker"], preview_at=quoted["preview_at"]
    )
    ids = []
    for _ in range(2):
        saved = pg_client.post(
            "/api/v1/admin/subscriptions/payments",
            json=payload,
            headers=headers(pg_case),
        )
        assert saved.status_code == 200, saved.text
        ids.append(saved.json()["data"]["id"])
    assert ids[0] == ids[1]
    pg_case.db.expire_all()
    assert pg_case.db.get(models.Tenant, tenant.id).subscription_end_date == expected
    assert pg_case.db.get(
        models.SubscriptionPayment, old_receipt_id
    ).payment_date == datetime(2025, 12, 1, 10)


@pytest.mark.parametrize(
    "field,value", [("duration_days", 3650), ("billing_cycle_unit", "year")]
)
def test_plan_term_change_invalidates_payment_quote(pg_case, pg_client, field, value):
    payload = dict(
        tenant_id=pg_case.tenant.id,
        plan_id=pg_case.plans["professional"].id,
        amount=400,
        payment_method="cash",
    )
    preview = pg_client.post(
        "/api/v1/admin/subscriptions/payments/preview",
        json=payload,
        headers=headers(pg_case),
    )
    assert preview.status_code == 200, preview.text
    quote = preview.json()["data"]
    plan = pg_case.db.get(models.SubscriptionPlan, payload["plan_id"])
    before = getattr(plan, field)
    try:
        setattr(plan, field, value)
        pg_case.db.commit()
        payload.update(
            preview_marker=quote["preview_marker"], preview_at=quote["preview_at"]
        )
        saved = pg_client.post(
            "/api/v1/admin/subscriptions/payments",
            json=payload,
            headers=headers(pg_case),
        )
        assert saved.status_code == 409, saved.text
        assert (
            pg_case.db.query(models.SubscriptionPayment)
            .filter_by(tenant_id=pg_case.tenant.id)
            .count()
            == 0
        )
    finally:
        setattr(plan, field, before)
        pg_case.db.commit()


def test_scheduled_monthly_plan_cannot_receive_legacy_duration_receipt(
    pg_case, pg_client
):
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    legacy = models.SubscriptionPlan(
        name=f"legacy_{tenant.id}",
        display_name_ar="Synthetic",
        price=1000,
        max_users=10,
        duration_days=3650,
        billing_cycle_unit="day",
        is_active=True,
    )
    pg_case.db.add(legacy)
    pg_case.db.flush()
    tenant.plan_id = legacy.id
    tenant.scheduled_downgrade_plan_id = pg_case.plans["professional"].id
    pg_case.db.commit()
    before = tenant.subscription_end_date
    payload = dict(
        tenant_id=tenant.id, plan_id=legacy.id, amount=1000, payment_method="cash"
    )
    for path in ("payments/preview", "payments"):
        response = pg_client.post(
            f"/api/v1/admin/subscriptions/{path}",
            json=payload,
            headers=headers(pg_case),
        )
        assert response.status_code == 409, response.text
    pg_case.db.expire_all()
    assert pg_case.db.get(models.Tenant, tenant.id).subscription_end_date == before
    assert (
        pg_case.db.query(models.SubscriptionPayment)
        .filter_by(tenant_id=tenant.id)
        .count()
        == 0
    )


@pytest.mark.parametrize("quoted", [False, True])
def test_unassigned_support_extension_retains_legacy_api(pg_case, pg_client, quoted):
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    tenant.plan_id = None
    tenant.plan = "legacy-unassigned"
    pg_case.db.commit()
    before = tenant.subscription_end_date
    payload = dict(
        extension_days=3,
        notes="Synthetic support",
        idempotency_key="unassigned-extension",
    )
    path = f"/api/v1/admin/tenants/{tenant.id}/renew"
    if quoted:
        preview = pg_client.post(
            path + "?preview=true", json=payload, headers=headers(pg_case)
        )
        assert preview.status_code == 200, preview.text
        data = preview.json()["data"]
        payload.update(
            preview_marker=data["preview_marker"], preview_at=data["preview_at"]
        )
    response = pg_client.post(path, json=payload, headers=headers(pg_case))
    assert response.status_code == 200, response.text
    from datetime import timedelta

    pg_case.db.expire_all()
    assert pg_case.db.get(
        models.Tenant, tenant.id
    ).subscription_end_date == before + timedelta(days=3)


def test_legacy_default_support_renewal_uses_day_term(pg_case, pg_client):
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    legacy = models.SubscriptionPlan(
        name=f"support_{tenant.id}",
        display_name_ar="Synthetic",
        price=400,
        max_users=5,
        duration_days=3650,
        billing_cycle_unit="day",
        is_active=True,
    )
    pg_case.db.add(legacy)
    pg_case.db.flush()
    tenant.plan_id = legacy.id
    pg_case.db.commit()
    before = tenant.subscription_end_date
    response = pg_client.post(
        f"/api/v1/admin/tenants/{tenant.id}/renew",
        json=dict(idempotency_key="legacy-default-support"),
        headers=headers(pg_case),
    )
    assert response.status_code == 200, response.text
    from datetime import timedelta

    pg_case.db.expire_all()
    assert pg_case.db.get(
        models.Tenant, tenant.id
    ).subscription_end_date == before + timedelta(days=3650)


@pytest.mark.parametrize("scenario", ["live_downgrade", "pending_future", "no_end"])
def test_system_assignment_uses_same_contract_guards(pg_case, pg_client, scenario):
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    target = pg_case.plans["essential"]
    if scenario == "live_downgrade":
        account = pg_case.db.query(models.User).filter_by(tenant_id=tenant.id).first()
        account.is_active = False
    if scenario == "pending_future":
        tenant.future_plan_id = target.id
        tenant.future_plan_start_date = tenant.subscription_end_date
        target = models.SubscriptionPlan(
            name=f"new_assignment_{tenant.id}",
            display_name_ar="Synthetic",
            price=1000,
            max_users=15,
            billing_cycle_unit="month",
            duration_days=30,
            is_active=True,
        )
        pg_case.db.add(target)
    elif scenario == "no_end":
        tenant.plan_id = None
        tenant.subscription_end_date = None
        target = pg_case.plans["professional"]
    pg_case.db.commit()
    before = tenant.subscription_end_date
    response = pg_client.post(
        f"/api/v1/admin/system/tenants/{tenant.id}/assign-plan?plan_id={target.id}",
        headers=headers(pg_case),
    )
    assert response.status_code == (200 if scenario == "no_end" else 409), response.text
    pg_case.db.expire_all()
    tenant = pg_case.db.get(models.Tenant, tenant.id)
    if scenario == "no_end":
        assert tenant.subscription_end_date is not None
    else:
        assert tenant.subscription_end_date == before


def test_payment_preview_is_read_only_matches_grant_and_replays(pg_case, pg_client):
    # Worked calendar case: existing Jan 31 -> one calendar month -> Feb 28.
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    tenant.subscription_end_date = datetime(2027, 1, 31, 10)
    tenant.billing_day_anchor = 31
    pg_case.db.commit()
    payload = dict(
        tenant_id=tenant.id,
        plan_id=pg_case.plans["professional"].id,
        amount=400,
        payment_method="cash",
    )
    writes = []
    from sqlalchemy.engine import Engine

    def track(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(" ", 1)[0].upper() in {
            "INSERT",
            "UPDATE",
            "DELETE",
        }:
            writes.append(statement)

    event.listen(Engine, "before_cursor_execute", track)
    try:
        preview = pg_client.post(
            "/api/v1/admin/subscriptions/payments/preview",
            json=payload,
            headers=headers(pg_case),
        )
    finally:
        event.remove(Engine, "before_cursor_execute", track)
    assert preview.status_code == 200, preview.text
    # Request audit middleware may append its access audit; business state is read-only.
    assert all(
        sql.lstrip().upper().startswith("INSERT INTO AUDIT_LOGS ") for sql in writes
    ), writes
    data = preview.json()["data"]
    assert data["amount"] in ("400.00", "400", 400)
    assert data["before"]["subscription_end_date"].startswith("2027-01-31T10:00:00")
    assert data["after"]["subscription_end_date"].startswith("2027-02-28T10:00:00")
    assert data["already_recorded"] is False
    payload.update(preview_marker=data["preview_marker"], preview_at=data["preview_at"])
    saved = pg_client.post(
        "/api/v1/admin/subscriptions/payments", json=payload, headers=headers(pg_case)
    )
    assert saved.status_code == 200, saved.text
    replay = pg_client.post(
        "/api/v1/admin/subscriptions/payments/preview",
        json=payload,
        headers=headers(pg_case),
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["already_recorded"] is True
    assert replay.json()["data"]["payment_id"] == saved.json()["data"]["id"]
    retried = pg_client.post(
        "/api/v1/admin/subscriptions/payments", json=payload, headers=headers(pg_case)
    )
    assert retried.status_code == 200, retried.text
    pg_case.db.expire_all()
    assert pg_case.db.get(models.Tenant, tenant.id).subscription_end_date == datetime(
        2027, 2, 28, 10
    )
    assert (
        pg_case.db.query(models.SubscriptionPayment)
        .filter_by(tenant_id=tenant.id)
        .count()
        == 1
    )


def test_stale_payment_preview_conflicts_without_receipt(pg_case, pg_client):
    payload = dict(
        tenant_id=pg_case.tenant.id,
        plan_id=pg_case.plans["professional"].id,
        amount=400,
        payment_method="cash",
    )
    preview = pg_client.post(
        "/api/v1/admin/subscriptions/payments/preview",
        json=payload,
        headers=headers(pg_case),
    )
    assert preview.status_code == 200, preview.text
    payload.update(
        preview_marker=preview.json()["data"]["preview_marker"],
        preview_at=preview.json()["data"]["preview_at"],
    )
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    tenant.policy_revision += 1
    pg_case.db.commit()
    saved = pg_client.post(
        "/api/v1/admin/subscriptions/payments", json=payload, headers=headers(pg_case)
    )
    assert saved.status_code == 409, saved.text
    assert (
        pg_case.db.query(models.SubscriptionPayment)
        .filter_by(tenant_id=tenant.id)
        .count()
        == 0
    )


def test_payment_preview_retains_super_admin_guard(pg_case, pg_client):
    from backend.auth import create_access_token

    user = pg_case.db.query(models.User).filter_by(tenant_id=pg_case.tenant.id).first()
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    response = pg_client.post(
        "/api/v1/admin/subscriptions/payments/preview",
        json=dict(
            tenant_id=pg_case.tenant.id,
            plan_id=pg_case.plans["professional"].id,
            amount=400,
            payment_method="cash",
        ),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403, response.text


def test_finalized_receipt_cannot_be_deleted_or_break_replay(pg_case, pg_client):
    payload = dict(
        tenant_id=pg_case.tenant.id,
        plan_id=pg_case.plans["professional"].id,
        amount=400,
        payment_method="cash",
    )
    saved = pg_client.post(
        "/api/v1/admin/subscriptions/payments", json=payload, headers=headers(pg_case)
    )
    assert saved.status_code == 200, saved.text
    payment_id = saved.json()["data"]["id"]
    denied = pg_client.delete(
        f"/api/v1/admin/subscriptions/payments/{payment_id}", headers=headers(pg_case)
    )
    assert denied.status_code == 409, denied.text
    pg_case.db.expire_all()
    assert pg_case.db.get(models.SubscriptionPayment, payment_id) is not None
    end = pg_case.db.get(models.Tenant, pg_case.tenant.id).subscription_end_date
    replay = pg_client.post(
        "/api/v1/admin/subscriptions/payments", json=payload, headers=headers(pg_case)
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["id"] == payment_id
    pg_case.db.expire_all()
    assert pg_case.db.get(models.Tenant, pg_case.tenant.id).subscription_end_date == end


@pytest.mark.parametrize("delay", [2, 6])
def test_expired_renewal_commits_exact_quoted_dates_within_preview_window(
    pg_case, pg_client, monkeypatch, delay
):
    from datetime import timedelta
    from backend.services.subscription_service import SubscriptionService

    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    tenant.subscription_end_date = datetime(2027, 1, 31, 10)
    pg_case.db.commit()
    quote_time = datetime(2027, 3, 31, 10)
    monkeypatch.setattr(SubscriptionService, "_utc_now_naive", lambda: quote_time)
    payload = dict(
        tenant_id=tenant.id,
        plan_id=pg_case.plans["professional"].id,
        amount=400,
        payment_method="cash",
    )
    response = pg_client.post(
        "/api/v1/admin/subscriptions/payments/preview",
        json=payload,
        headers=headers(pg_case),
    )
    assert response.status_code == 200, response.text
    quoted = response.json()["data"]
    payload.update(
        preview_marker=quoted["preview_marker"], preview_at=quoted["preview_at"]
    )
    monkeypatch.setattr(
        SubscriptionService,
        "_utc_now_naive",
        lambda: quote_time + timedelta(minutes=delay),
    )
    saved = pg_client.post(
        "/api/v1/admin/subscriptions/payments", json=payload, headers=headers(pg_case)
    )
    if delay == 6:
        assert saved.status_code == 409, saved.text
        assert (
            pg_case.db.query(models.SubscriptionPayment)
            .filter_by(tenant_id=tenant.id)
            .count()
            == 0
        )
        return
    assert saved.status_code == 200, saved.text
    pg_case.db.expire_all()
    end = pg_case.db.get(models.Tenant, tenant.id).subscription_end_date
    assert end.isoformat() == quoted["after"]["subscription_end_date"]


def test_explicit_manual_extension_has_read_only_preview_and_stable_replay(
    pg_case, pg_client
):
    tenant = pg_case.db.get(models.Tenant, pg_case.tenant.id)
    end = tenant.subscription_end_date
    payload = dict(
        plan_id=pg_case.plans["professional"].id,
        extension_days=3,
        notes="Synthetic support extension, no receipt",
        idempotency_key="synthetic-free-extension",
    )
    preview = pg_client.post(
        f"/api/v1/admin/tenants/{tenant.id}/renew?preview=true",
        json=payload,
        headers=headers(pg_case),
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()["data"]
    pg_case.db.expire_all()
    assert pg_case.db.get(models.Tenant, tenant.id).subscription_end_date == end
    payload.update(preview_marker=data["preview_marker"], preview_at=data["preview_at"])
    for _ in range(2):
        saved = pg_client.post(
            f"/api/v1/admin/tenants/{tenant.id}/renew",
            json=payload,
            headers=headers(pg_case),
        )
        assert saved.status_code == 200, saved.text
    pg_case.db.expire_all()
    assert (
        pg_case.db.get(models.Tenant, tenant.id).subscription_end_date.isoformat()
        == data["subscription_end_date"]
    )
    assert (
        pg_case.db.query(models.SubscriptionPayment)
        .filter_by(tenant_id=tenant.id)
        .count()
        == 0
    )
