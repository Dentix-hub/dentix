"""Webhook signing and verification helpers."""

from typing import Dict, Any
import hashlib
import hmac
import json
from datetime import datetime, timezone


class WebhookService:
    """Service for sending webhooks with signature verification."""

    def __init__(self, secret: str):
        self.secret = secret

    def generate_signature(self, payload: Dict[str, Any], timestamp: str) -> str:
        """Generate HMAC SHA256 signature."""
        raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return self.generate_raw_signature(raw_payload, timestamp)

    def generate_raw_signature(self, raw_payload: bytes, timestamp: str) -> str:
        """Sign the exact request bytes to prevent parser/canonicalization gaps."""
        signed_payload = timestamp.encode("utf-8") + b"." + raw_payload
        return hmac.new(
            self.secret.encode("utf-8"), signed_payload, hashlib.sha256
        ).hexdigest()

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime:
        value = timestamp.strip()
        if value.isdigit():
            return datetime.fromtimestamp(int(value), tz=timezone.utc)

        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def verify_raw_signature(
        self,
        raw_payload: bytes,
        timestamp: str,
        signature: str,
        *,
        max_age_seconds: int = 300,
        now: datetime | None = None,
    ) -> bool:
        """Verify signature and reject stale or future replay attempts."""
        try:
            signed_at = self._parse_timestamp(timestamp)
        except (TypeError, ValueError, OverflowError):
            return False

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        age_seconds = abs((current_time - signed_at).total_seconds())
        if age_seconds > max_age_seconds:
            return False

        provided_signature = signature.strip()
        if provided_signature.startswith("sha256="):
            provided_signature = provided_signature[7:]
        expected_signature = self.generate_raw_signature(raw_payload, timestamp)
        return hmac.compare_digest(provided_signature, expected_signature)

    def prepare_payload(self, event: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare stamped payload with signature."""
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {"event": event, "data": data, "timestamp": timestamp}

        signature = self.generate_signature(payload, timestamp)

        return {
            "payload": payload,
            "headers": {
                "X-Webhook-Signature": signature,
                "X-Webhook-Timestamp": timestamp,
            },
        }
