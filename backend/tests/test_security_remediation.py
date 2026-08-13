import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import pytest
import jwt
from pydantic import ValidationError

from backend import auth
from backend.core.tenancy import get_current_tenant_id, is_super_admin_bypass
from backend.middleware.tenant import TenantMiddleware
from backend.schemas.system_log import SystemErrorCreate
from backend.schemas.tenant import SubscriptionWebhookEvent
from backend.services.oauth_state import (
    create_backup_oauth_state,
    read_backup_oauth_state,
)
from backend.services.subscription_service import SubscriptionService


def test_webhook_signature_accepts_valid_body_and_rejects_tampering():
    body = b'{"provider_reference":"sub_123"}'
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    secret = "provider-secret"
    digest = hmac.new(
        secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()

    assert SubscriptionService.verify_webhook_signature(
        body, timestamp, f"sha256={digest}", secret
    )
    assert not SubscriptionService.verify_webhook_signature(
        body + b" ", timestamp, digest, secret
    )


def test_webhook_signature_rejects_replay_window():
    old_timestamp = str(
        int(
            (
                datetime.now(timezone.utc)
                - timedelta(seconds=SubscriptionService.WEBHOOK_TOLERANCE_SECONDS + 1)
            ).timestamp()
        )
    )
    assert not SubscriptionService.verify_webhook_signature(
        b"{}", old_timestamp, "invalid", "secret"
    )


def test_webhook_payload_has_no_client_owned_tenant_or_plan():
    event = SubscriptionWebhookEvent.model_validate(
        {
            "provider": "testpay",
            "provider_payment_id": "pay_123",
            "provider_status": "paid",
            "provider_reference": "sub_reference_123",
            "amount": 100,
            "currency": "EGP",
            "tenant_id": 999,
            "plan_id": 999,
        }
    )
    assert "tenant_id" not in event.model_dump()
    assert "plan_id" not in event.model_dump()

    with pytest.raises(ValidationError):
        SubscriptionWebhookEvent.model_validate(
            {
                "provider": "testpay",
                "provider_payment_id": "pay_123",
                "provider_status": "paid",
                "provider_reference": "sub_reference_123",
                "amount": -1,
            }
        )


def test_public_error_schema_drops_identity_fields():
    error = SystemErrorCreate.model_validate(
        {
            "message": "failed",
            "source": "FRONTEND",
            "tenant_id": 999,
            "user_id": 999,
        }
    )
    assert "tenant_id" not in error.model_dump()
    assert "user_id" not in error.model_dump()


def test_google_oauth_state_is_signed_and_scoped():
    state = create_backup_oauth_state(42)
    assert read_backup_oauth_state(state) == "42"

    payload = jwt.decode(state, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    payload["purpose"] = "different-purpose"
    forged = jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
    with pytest.raises(ValueError, match="Invalid OAuth state"):
        read_backup_oauth_state(forged)


@pytest.mark.anyio
async def test_tenant_middleware_reads_cookie_and_cleans_context():
    token = auth.create_access_token(
        {"sub": "cookie-user", "tenant_id": 77, "role": "doctor"}
    )
    request = type(
        "RequestStub",
        (),
        {
            "headers": {},
            "cookies": {"access_token": token},
        },
    )()

    async def next_handler(_request):
        assert get_current_tenant_id() == 77
        assert not is_super_admin_bypass()
        return "ok"

    middleware = TenantMiddleware(app=lambda scope, receive, send: None)
    assert await middleware.dispatch(request, next_handler) == "ok"
    assert get_current_tenant_id() is None
    assert not is_super_admin_bypass()


def test_local_postgres_disables_ssl_by_default():
    from backend.database import _resolve_postgres_ssl_mode

    assert (
        _resolve_postgres_ssl_mode(
            "postgresql://test_user:test_pass@localhost:5432/dentix_test",
            None,
        )
        == "disable"
    )
    assert (
        _resolve_postgres_ssl_mode(
            "postgresql://test_user:test_pass@[::1]:5432/dentix_test",
            None,
        )
        == "disable"
    )


def test_remote_postgres_keeps_secure_ssl_default():
    from backend.database import _apply_postgres_ssl_mode, _resolve_postgres_ssl_mode

    remote_url = "postgresql://user:pass@db.example.com:5432/dentix"
    assert _resolve_postgres_ssl_mode(remote_url, None) == "require"
    assert _resolve_postgres_ssl_mode(remote_url, "verify-full") == "verify-full"

    legacy_url = f"{remote_url}?sslmode=require&application_name=dentix"
    assert _resolve_postgres_ssl_mode(legacy_url, "verify-full") == "verify-full"
    assert _apply_postgres_ssl_mode(legacy_url, "verify-full") == (
        f"{remote_url}?sslmode=verify-full&application_name=dentix"
    )
    assert _apply_postgres_ssl_mode(remote_url, "verify-full") == (
        f"{remote_url}?sslmode=verify-full"
    )
