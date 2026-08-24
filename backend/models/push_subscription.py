from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PushSubscription(Base):
    """
    A per-installation push delivery target (plan §12.2).

    Long-lived push eligibility is bound to the stable session identity
    (`session_sid`, i.e. `User.active_session_id`) — NOT to the rotating
    `UserSession.id` row, which refresh-token rotation replaces while the
    session family stays valid. When the user's active session changes
    (logout, session mismatch, single-session replacement), subscriptions
    carrying the previous sid stop being delivery-eligible.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    # Nullable to mirror users.tenant_id (super admins have no tenant).
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    provider: Mapped[str] = mapped_column(String, default="web_push")
    # Push service endpoints are long-lived URLs; Text avoids length surprises.
    endpoint: Mapped[str] = mapped_column(Text, index=True)
    p256dh_key: Mapped[str] = mapped_column(String)
    auth_key: Mapped[str] = mapped_column(String)
    # Only used if a provider-specific legacy path is ever retained.
    provider_token: Mapped[str | None] = mapped_column(String, nullable=True)

    # Client-generated, non-secret installation identifier.
    device_installation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # Stable session identity (User.active_session_id) at subscription time.
    session_sid: Mapped[str] = mapped_column(String, index=True)

    platform: Mapped[str | None] = mapped_column(String, nullable=True)
    browser_family: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    # Retained for fast eligibility filtering; derived from revoked_at.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    user = relationship("User", backref="push_subscriptions")
