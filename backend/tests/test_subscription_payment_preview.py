"""Receipt preview must use the actual period grant without writing records."""

from datetime import datetime
import pytest
from sqlalchemy import event

from backend import models
from backend.tests import test_commercial_plan_completion as fixtures

pg_case = fixtures.pg_case
pg_client = fixtures.pg_client
headers = fixtures.headers


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
