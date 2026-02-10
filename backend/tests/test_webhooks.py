"""
Webhook Tests
Tests for WebhookService signature verification and payload structure.
"""

from backend.services.webhook_service import WebhookService


def test_webhook_signature_generation():
    """Signature should be consistent and verifiable."""
    service = WebhookService(secret="test_secret")
    payload = {"id": 1, "status": "paid"}
    timestamp = "2026-01-01T12:00:00Z"

    sig1 = service.generate_signature(payload, timestamp)
    sig2 = service.generate_signature(payload, timestamp)

    assert sig1 == sig2
    assert len(sig1) == 64  # SHA256 hex digest length


def test_payload_preparation():
    """Prepared payload should contain headers and signature."""
    service = WebhookService(secret="test_secret")
    event = "payment.received"
    data = {"amount": 100}

    result = service.prepare_payload(event, data)

    assert "payload" in result
    assert "headers" in result
    assert "X-Webhook-Signature" in result["headers"]
    assert result["payload"]["event"] == event


def test_signature_changes_with_secret():
    """Different secrets should produce different signatures."""
    service1 = WebhookService(secret="secret_1")
    service2 = WebhookService(secret="secret_2")
    payload = {"id": 1}
    timestamp = "2026-01-01T12:00:00Z"

    assert service1.generate_signature(
        payload, timestamp
    ) != service2.generate_signature(payload, timestamp)
