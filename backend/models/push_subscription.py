from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PushSubscription(Base):
    """
    A per-installation push delivery target (plan §12.2).

    Delivery eligibility is bound to the device-scoped JWT session identity
    (`session_sid`), which is persisted in `UserSession.device_info` and remains
    stable across refresh-token rotation. Multiple active device sessions may
    coexist; revoking one sid only disables subscriptions for that device.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    provider: Mapped[str] = mapped_column(String, default="web_push")
    endpoint: Mapped[str] = mapped_column(Text, index=True)
    p256dh_key: Mapped[str] = mapped_column(String)
    auth_key: Mapped[str] = mapped_column(String)
    provider_token: Mapped[str | None] = mapped_column(String, nullable=True)

    device_installation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # Stable per-device session identity copied from the authenticated JWT sid.
    session_sid: Mapped[str] = mapped_column(String, index=True)

    platform: Mapped[str | None] = mapped_column(String, nullable=True)
    browser_family: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    user = relationship("User", backref="push_subscriptions")
