from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=512)


class PushSubscriptionCreate(BaseModel):
    """Registration payload for the current browser installation.

    `user_id`, `tenant_id` and `session_sid` are NEVER accepted from the body:
    they are derived from the authenticated request context (plan §12.3).
    """

    endpoint: str = Field(min_length=1, max_length=2048)
    keys: PushKeys
    provider: Literal["web_push"] = "web_push"
    device_installation_id: Optional[str] = Field(default=None, max_length=128)
    platform: Optional[Literal["android", "ios", "desktop", "unknown"]] = None
    browser_family: Optional[str] = Field(default=None, max_length=64)

    @field_validator("endpoint")
    @classmethod
    def endpoint_must_be_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("Push endpoint must be an HTTPS URL")
        return value


class PushSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    endpoint: str
    device_installation_id: Optional[str] = None
    platform: Optional[str] = None
    browser_family: Optional[str] = None
    created_at: datetime
    last_seen_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool


class PushSubscriptionRefresh(BaseModel):
    """Rotate the keys of an existing subscription (pushsubscriptionchange)."""

    endpoint: str = Field(min_length=1, max_length=2048)
    keys: PushKeys
