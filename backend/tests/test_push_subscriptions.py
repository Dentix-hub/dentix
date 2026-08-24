"""Tests for the device-session-aware push subscription stack (plan §12 / PR-PWA-05)."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend import models, schemas
from backend.auth import create_access_token
from backend.services import web_push_service
from backend.services.web_push_service import DeliveryResult, WebPushService

pytestmark = pytest.mark.asyncio


def _subscription_data(endpoint="https://push.example/ep-1", device=None):
    return schemas.PushSubscriptionCreate(
        endpoint=endpoint,
        keys=schemas.PushKeys(p256dh="p256dh-key", auth="auth-key"),
        device_installation_id=device,
        platform="android",
        browser_family="chrome",
    )


async def _make_user(async_session, username="pushdoc", with_tenant=True):
    tenant_id = None
    if with_tenant:
        tenant = models.Tenant(name=f"Push Clinic {uuid.uuid4().hex[:8]}", is_active=True)
        async_session.add(tenant)
        await async_session.flush()
        tenant_id = tenant.id
    user = models.User(
        username=f"{username}_{uuid.uuid4().hex[:8]}",
        email=f"{username}_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="x",
        role="doctor",
        tenant_id=tenant_id,
        is_active=True,
        active_session_id=None,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


async def _activate_session(async_session, user, sid):
    token_hash = hashlib.sha256(f"{sid}-{uuid.uuid4().hex}".encode()).hexdigest()
    session = models.UserSession(
        user_id=user.id,
        token_hash=token_hash,
        ip_address="127.0.0.1",
        user_agent="pytest",
        device_info=sid,
        expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).replace(tzinfo=None),
        is_active=True,
    )
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)
    return session


@pytest.fixture
async def async_session(async_engine_fixture):
    maker = async_sessionmaker(bind=async_engine_fixture, expire_on_commit=False)
    async with maker() as session:
        yield session


class FakeProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def send(self, subscription, title, body, data=None):
        self.calls.append(subscription.endpoint)
        return self.result


@pytest.fixture
def scripted_provider(monkeypatch):
    def _install(result):
        provider = FakeProvider(result)
        monkeypatch.setattr(
            web_push_service, "get_delivery_provider", lambda name: provider
        )
        return provider

    return _install


async def test_second_device_does_not_overwrite_first(async_session):
    user = await _make_user(async_session)

    first = await WebPushService.register_subscription(
        async_session, user, "sid-1", _subscription_data("https://push.example/dev-1", "device-1")
    )
    second = await WebPushService.register_subscription(
        async_session, user, "sid-2", _subscription_data("https://push.example/dev-2", "device-2")
    )

    active = await WebPushService.list_user_subscriptions(async_session, user.id)
    assert len(active) == 2
    assert {first.endpoint, second.endpoint} == {s.endpoint for s in active}
    assert {s.session_sid for s in active} == {"sid-1", "sid-2"}


async def test_resubscribing_same_endpoint_replaces_not_duplicates(async_session):
    user = await _make_user(async_session)

    await WebPushService.register_subscription(
        async_session, user, "sid-1", _subscription_data("https://push.example/dev-1", "device-1")
    )
    await WebPushService.register_subscription(
        async_session, user, "sid-1", _subscription_data("https://push.example/dev-1", "device-1")
    )

    active = await WebPushService.list_user_subscriptions(async_session, user.id)
    assert len(active) == 1


async def test_subscription_binds_tenant_and_session_from_context(async_session):
    user = await _make_user(async_session)

    subscription = await WebPushService.register_subscription(
        async_session, user, "stable-sid", _subscription_data()
    )

    assert subscription.user_id == user.id
    assert subscription.tenant_id == user.tenant_id
    assert subscription.session_sid == "stable-sid"
    assert subscription.revoked_at is None


async def test_rejects_revoking_another_users_subscription(async_session):
    owner = await _make_user(async_session, username="owner")
    attacker = await _make_user(async_session, username="attacker")

    subscription = await WebPushService.register_subscription(
        async_session, owner, "sid-owner", _subscription_data()
    )

    revoked = await WebPushService.revoke_subscription(async_session, attacker.id, subscription.id)
    assert revoked is False
    still_active = await WebPushService.list_user_subscriptions(async_session, owner.id)
    assert len(still_active) == 1


async def test_session_revocation_disassociates_only_that_installation(async_session):
    user = await _make_user(async_session)

    await WebPushService.register_subscription(
        async_session, user, "old-sid", _subscription_data("https://push.example/old")
    )
    await WebPushService.register_subscription(
        async_session, user, "new-sid", _subscription_data("https://push.example/new")
    )

    revoked_count = await WebPushService.revoke_for_session(async_session, user.id, "old-sid")
    assert revoked_count == 1

    active = await WebPushService.list_user_subscriptions(async_session, user.id)
    assert [s.endpoint for s in active] == ["https://push.example/new"]


async def test_fanout_delivers_to_all_active_devices_and_revokes_stale(async_session, scripted_provider):
    user = await _make_user(async_session)
    await _activate_session(async_session, user, "sid-a")
    await _activate_session(async_session, user, "sid-b")

    await WebPushService.register_subscription(
        async_session, user, "sid-a", _subscription_data("https://push.example/a")
    )
    await WebPushService.register_subscription(
        async_session, user, "sid-b", _subscription_data("https://push.example/b")
    )
    await WebPushService.register_subscription(
        async_session, user, "stale-sid", _subscription_data("https://push.example/stale")
    )

    provider = scripted_provider(DeliveryResult.SENT)
    summary = await WebPushService.send_to_user(
        async_session, user.id, "DENTIX", "لديك تحديث جديد في جدول المواعيد"
    )

    assert summary == {"sent": 2, "revoked": 1, "skipped": 0}
    assert set(provider.calls) == {"https://push.example/a", "https://push.example/b"}
    active = await WebPushService.list_user_subscriptions(async_session, user.id)
    assert {s.endpoint for s in active} == {"https://push.example/a", "https://push.example/b"}


async def test_invalid_endpoint_is_revoked_after_permanent_failure(async_session, scripted_provider):
    user = await _make_user(async_session)
    await _activate_session(async_session, user, "sid-1")

    await WebPushService.register_subscription(
        async_session, user, "sid-1", _subscription_data("https://push.example/gone")
    )
    scripted_provider(DeliveryResult.INVALID)

    summary = await WebPushService.send_to_user(async_session, user.id, "DENTIX", "تنبيه")
    assert summary["revoked"] == 1
    active = await WebPushService.list_user_subscriptions(async_session, user.id)
    assert active == []


async def test_inactive_user_never_receives_delivery(async_session, scripted_provider):
    user = await _make_user(async_session)
    await _activate_session(async_session, user, "sid-1")
    user.is_active = False
    async_session.add(user)
    await async_session.commit()

    await WebPushService.register_subscription(
        async_session, user, "sid-1", _subscription_data()
    )
    provider = scripted_provider(DeliveryResult.SENT)

    summary = await WebPushService.send_to_user(async_session, user.id, "DENTIX", "تنبيه")
    assert summary == {"sent": 0, "revoked": 0, "skipped": 0}
    assert provider.calls == []


# ---------------------------------------------------------------------------
# API contract
# ---------------------------------------------------------------------------


def _auth_token_for(user, sid=None):
    data = {
        "sub": user.username,
        "role": user.role,
        "tenant_id": user.tenant_id,
    }
    if sid:
        data["sid"] = sid
    return create_access_token(data=data)


async def _seed_api_user(async_session):
    user = await _make_user(async_session, username="apiuser")
    sid = f"sid-{uuid.uuid4().hex[:12]}"
    await _activate_session(async_session, user, sid)
    return user, sid


async def test_register_endpoint_binds_token_sid(client, async_engine_fixture):
    maker = async_sessionmaker(bind=async_engine_fixture, expire_on_commit=False)
    async with maker() as session:
        user, sid = await _seed_api_user(session)
        token = _auth_token_for(user, sid)

        response = client.post(
            "/api/v1/push/subscriptions",
            json={
                "endpoint": "https://push.example/api-1",
                "keys": {"p256dh": "k1", "auth": "k2"},
                "platform": "android",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["success"] is True

        stored = (
            await session.execute(
                select(models.PushSubscription).where(
                    models.PushSubscription.endpoint == "https://push.example/api-1"
                )
            )
        ).scalars().first()
        assert stored is not None
        assert stored.session_sid == sid
        assert stored.user_id == user.id
        assert stored.tenant_id == user.tenant_id


async def test_register_requires_sid_claim(client, async_engine_fixture):
    maker = async_sessionmaker(bind=async_engine_fixture, expire_on_commit=False)
    async with maker() as session:
        user, _ = await _seed_api_user(session)
        token_without_sid = _auth_token_for(user, sid=None)

        response = client.post(
            "/api/v1/push/subscriptions",
            json={
                "endpoint": "https://push.example/api-2",
                "keys": {"p256dh": "k1", "auth": "k2"},
            },
            headers={"Authorization": f"Bearer {token_without_sid}"},
        )
        assert response.status_code == 401


async def test_me_lists_only_active_and_owned(client, async_engine_fixture):
    maker = async_sessionmaker(bind=async_engine_fixture, expire_on_commit=False)
    async with maker() as session:
        user, sid = await _seed_api_user(session)
        other = await _make_user(session, username="other")
        token = _auth_token_for(user, sid)

        mine = await WebPushService.register_subscription(
            session, user, sid, _subscription_data("https://push.example/mine")
        )
        await WebPushService.register_subscription(
            session, other, "other-sid", _subscription_data("https://push.example/theirs")
        )
        await WebPushService.revoke_subscription(session, user.id, mine.id)

        response = client.get(
            "/api/v1/push/subscriptions/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        endpoints = [item["endpoint"] for item in response.json()["data"]]
        assert "https://push.example/mine" not in endpoints
        assert "https://push.example/theirs" not in endpoints


async def test_delete_other_users_subscription_returns_404(client, async_engine_fixture):
    maker = async_sessionmaker(bind=async_engine_fixture, expire_on_commit=False)
    async with maker() as session:
        user, sid = await _seed_api_user(session)
        other = await _make_user(session, username="victim")
        theirs = await WebPushService.register_subscription(
            session, other, "victim-sid", _subscription_data("https://push.example/victim")
        )
        token = _auth_token_for(user, sid)

        response = client.delete(
            f"/api/v1/push/subscriptions/{theirs.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        still_active = await WebPushService.list_user_subscriptions(session, other.id)
        assert len(still_active) == 1


async def test_revoke_all_for_user(client, async_engine_fixture):
    maker = async_sessionmaker(bind=async_engine_fixture, expire_on_commit=False)
    async with maker() as session:
        user, sid = await _seed_api_user(session)
        await WebPushService.register_subscription(
            session, user, sid, _subscription_data("https://push.example/a", "dev-a")
        )
        await WebPushService.register_subscription(
            session, user, sid, _subscription_data("https://push.example/b", "dev-b")
        )
        token = _auth_token_for(user, sid)

        response = client.delete(
            "/api/v1/push/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["revoked"] == 2
        active = await WebPushService.list_user_subscriptions(session, user.id)
        assert active == []
