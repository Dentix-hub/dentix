"""Standards-based Web Push delivery (plan §12).

Provider boundary:

    NotificationDeliveryProvider
            |-- WebPushProvider          # canonical PWA path (VAPID)
            `-- FirebaseNativeProvider   # legacy/native best-effort path

Push is a delivery channel only: the durable notification record remains the
source of truth. Delivery eligibility is device-scoped: a subscription is
deliverable only while its `session_sid` resolves to an active UserSession for
that user. Multiple active devices can therefore receive notifications without
revoking or suppressing one another.
"""

import abc
import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from .auth_service import AuthService

logger = logging.getLogger("smart_clinic")

MAX_ACTIVE_SUBSCRIPTIONS_PER_USER = 8


class DeliveryResult(str, Enum):
    SENT = "sent"
    INVALID = "invalid"
    RETRYABLE = "retryable"
    NOT_CONFIGURED = "not_configured"
    INELIGIBLE = "ineligible"


class NotificationDeliveryProvider(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    async def send(
        self,
        subscription: models.PushSubscription,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> DeliveryResult:
        raise NotImplementedError


class WebPushProvider(NotificationDeliveryProvider):
    name = "web_push"

    def __init__(self) -> None:
        self._vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
        self._vapid_subject = os.getenv("VAPID_SUBJECT", "mailto:support@dentixs.app")

    @property
    def is_configured(self) -> bool:
        return bool(self._vapid_private_key)

    async def send(
        self,
        subscription: models.PushSubscription,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> DeliveryResult:
        if not self.is_configured:
            logger.warning("VAPID_PRIVATE_KEY not set; web push delivery disabled.")
            return DeliveryResult.NOT_CONFIGURED

        try:
            from pywebpush import webpush
        except ImportError:
            logger.error("pywebpush is not installed; web push delivery disabled.")
            return DeliveryResult.NOT_CONFIGURED

        payload = json.dumps({
            "notification": {
                "title": title,
                "body": body,
                "lang": "ar",
                "dir": "rtl",
                **({"navigate": data["navigate"]} if data and data.get("navigate") else {}),
            },
        }).encode("utf-8")

        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh_key,
                        "auth": subscription.auth_key,
                    },
                },
                data=payload,
                vapid_private_key=self._vapid_private_key,
                vapid_claims={"sub": self._vapid_subject},
            )
            return DeliveryResult.SENT
        except Exception as exc:  # noqa: BLE001 - provider boundary
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in (404, 410):
                logger.info(
                    "Push endpoint permanently invalid (status=%s); revoking.",
                    status_code,
                )
                return DeliveryResult.INVALID
            logger.error("Web push delivery failed: %s", exc)
            return DeliveryResult.RETRYABLE


class FirebaseNativeProvider(NotificationDeliveryProvider):
    name = "firebase"

    def __init__(self) -> None:
        from ..core.firebase_client import firebase_client
        self._client = firebase_client

    async def send(
        self,
        subscription: models.PushSubscription,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> DeliveryResult:
        if not self._client.is_ready:
            return DeliveryResult.NOT_CONFIGURED
        token = subscription.provider_token
        if not token:
            return DeliveryResult.INELIGIBLE
        sent = self._client.send_push_notification(token=token, title=title, body=body, data=data)
        return DeliveryResult.SENT if sent else DeliveryResult.RETRYABLE


_web_push_provider = WebPushProvider()
_firebase_provider = FirebaseNativeProvider()

_PROVIDERS = {
    _web_push_provider.name: _web_push_provider,
    _firebase_provider.name: _firebase_provider,
}


def get_delivery_provider(name: str) -> NotificationDeliveryProvider:
    return _PROVIDERS.get(name, _web_push_provider)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class WebPushService:
    """Subscription lifecycle + fanout for the current-user push surface."""

    @staticmethod
    async def register_subscription(
        db: AsyncSession,
        user: models.User,
        session_sid: str,
        data,
    ) -> models.PushSubscription:
        now = _utcnow()

        existing = (
            await db.execute(
                select(models.PushSubscription).where(
                    models.PushSubscription.user_id == user.id,
                    models.PushSubscription.endpoint == data.endpoint,
                )
            )
        ).scalars().all()
        for row in existing:
            if row.revoked_at is None:
                row.revoked_at = now
                row.is_active = False

        if data.device_installation_id:
            stale_device_rows = (
                await db.execute(
                    select(models.PushSubscription).where(
                        models.PushSubscription.user_id == user.id,
                        models.PushSubscription.device_installation_id == data.device_installation_id,
                        models.PushSubscription.revoked_at.is_(None),
                    )
                )
            ).scalars().all()
            for row in stale_device_rows:
                row.revoked_at = now
                row.is_active = False

        active_count = len(
            (
                await db.execute(
                    select(models.PushSubscription).where(
                        models.PushSubscription.user_id == user.id,
                        models.PushSubscription.revoked_at.is_(None),
                    )
                )
            ).scalars().all()
        )
        if active_count >= MAX_ACTIVE_SUBSCRIPTIONS_PER_USER:
            oldest = (
                await db.execute(
                    select(models.PushSubscription)
                    .where(
                        models.PushSubscription.user_id == user.id,
                        models.PushSubscription.revoked_at.is_(None),
                    )
                    .order_by(models.PushSubscription.last_seen_at.asc())
                    .limit(1)
                )
            ).scalars().first()
            if oldest is not None:
                oldest.revoked_at = now
                oldest.is_active = False

        subscription = models.PushSubscription(
            user_id=user.id,
            tenant_id=user.tenant_id,
            provider=data.provider,
            endpoint=data.endpoint,
            p256dh_key=data.keys.p256dh,
            auth_key=data.keys.auth,
            device_installation_id=data.device_installation_id,
            session_sid=session_sid,
            platform=data.platform,
            browser_family=data.browser_family,
            last_seen_at=now,
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def refresh_subscription(
        db: AsyncSession,
        user: models.User,
        session_sid: str,
        endpoint: str,
        p256dh: str,
        auth_key: str,
    ) -> Optional[models.PushSubscription]:
        subscription = (
            await db.execute(
                select(models.PushSubscription).where(
                    models.PushSubscription.user_id == user.id,
                    models.PushSubscription.endpoint == endpoint,
                    models.PushSubscription.revoked_at.is_(None),
                )
            )
        ).scalars().first()
        if subscription is None:
            return None
        subscription.p256dh_key = p256dh
        subscription.auth_key = auth_key
        subscription.session_sid = session_sid
        subscription.last_seen_at = _utcnow()
        await db.commit()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def list_user_subscriptions(
        db: AsyncSession,
        user_id: int,
        active_only: bool = True,
    ) -> List[models.PushSubscription]:
        conditions = [models.PushSubscription.user_id == user_id]
        if active_only:
            conditions.append(models.PushSubscription.revoked_at.is_(None))
        result = await db.execute(
            select(models.PushSubscription)
            .where(*conditions)
            .order_by(models.PushSubscription.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def revoke_subscription(
        db: AsyncSession,
        user_id: int,
        subscription_id: int,
    ) -> bool:
        subscription = (
            await db.execute(
                select(models.PushSubscription).where(
                    models.PushSubscription.id == subscription_id,
                    models.PushSubscription.user_id == user_id,
                )
            )
        ).scalars().first()
        if subscription is None or subscription.revoked_at is not None:
            return False
        subscription.revoked_at = _utcnow()
        subscription.is_active = False
        await db.commit()
        return True

    @staticmethod
    async def revoke_all_for_user(db: AsyncSession, user_id: int) -> int:
        now = _utcnow()
        subscriptions = await WebPushService.list_user_subscriptions(db, user_id)
        for subscription in subscriptions:
            subscription.revoked_at = now
            subscription.is_active = False
        await db.commit()
        return len(subscriptions)

    @staticmethod
    async def revoke_for_session(db: AsyncSession, user_id: int, session_sid: str) -> int:
        now = _utcnow()
        subscriptions = (
            await db.execute(
                select(models.PushSubscription).where(
                    models.PushSubscription.user_id == user_id,
                    models.PushSubscription.session_sid == session_sid,
                    models.PushSubscription.revoked_at.is_(None),
                )
            )
        ).scalars().all()
        for subscription in subscriptions:
            subscription.revoked_at = now
            subscription.is_active = False
        await db.commit()
        return len(subscriptions)

    @staticmethod
    async def send_to_user(
        db: AsyncSession,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        user = (
            await db.execute(
                select(models.User).where(models.User.id == user_id, models.User.is_active == True)  # noqa: E712
            )
        ).scalars().first()
        if user is None:
            return {"sent": 0, "revoked": 0, "skipped": 0}

        subscriptions = await WebPushService.list_user_subscriptions(db, user_id)
        summary = {"sent": 0, "revoked": 0, "skipped": 0}

        for subscription in subscriptions:
            active_session = await AuthService.get_active_session_by_sid(
                db, user_id, subscription.session_sid
            )
            if active_session is None:
                subscription.revoked_at = _utcnow()
                subscription.is_active = False
                summary["revoked"] += 1
                continue

            provider = get_delivery_provider(subscription.provider)
            result = await provider.send(subscription, title, body, data)

            if result is DeliveryResult.SENT:
                subscription.last_seen_at = _utcnow()
                summary["sent"] += 1
            elif result is DeliveryResult.INVALID:
                subscription.revoked_at = _utcnow()
                subscription.is_active = False
                summary["revoked"] += 1
            else:
                summary["skipped"] += 1

        await db.commit()
        logger.info("Push fanout for user %s: %s", user_id, summary)
        return summary


web_push_service = WebPushService()
