"""
Mock Webhook Service

Mock implementation of a webhook service for testing infrastructure.
Actual implementation would likely use httpx to send requests.
"""

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
        data = f"{timestamp}.{json.dumps(payload, separators=(',', ':'))}"
        return hmac.new(self.secret.encode(), data.encode(), hashlib.sha256).hexdigest()

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
