"""
Unit Tests for Core Services.

Tests for encryption, logging, and utility functions.
"""


# ============================================
# ENCRYPTION TESTS
# ============================================


class TestEncryptionManager:
    """Tests for EncryptionManager class."""

    def test_generate_key_returns_valid_key(self):
        """Test that generated key is valid format."""
        from backend.core.security import EncryptionManager

        key = EncryptionManager.generate_key()

        assert key is not None
        assert len(key) == 44  # Fernet key length
        assert EncryptionManager.validate_key(key)

    def test_validate_key_rejects_invalid_keys(self):
        """Test that invalid keys are rejected."""
        from backend.core.security import EncryptionManager

        assert not EncryptionManager.validate_key("")
        assert not EncryptionManager.validate_key("short")
        assert not EncryptionManager.validate_key("x" * 100)

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption produces original value."""
        from backend.core.security import EncryptionManager

        # Generate key for testing
        key = EncryptionManager.generate_key()
        manager = EncryptionManager(key=key)

        original = "sensitive patient data"
        encrypted = manager.encrypt(original)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == original
        assert encrypted != original

    def test_encrypt_returns_none_for_none(self):
        """Test that None input returns None."""
        from backend.core.security import EncryptionManager

        key = EncryptionManager.generate_key()
        manager = EncryptionManager(key=key)

        assert manager.encrypt(None) is None
        assert manager.decrypt(None) is None


# ============================================
# EXCEPTION TESTS
# ============================================


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_validation_exception_has_correct_status(self):
        """Test ValidationException has 422 status."""
        from backend.core.exceptions import ValidationException

        exc = ValidationException("Invalid input", field="email")

        assert exc.status_code == 422
        assert exc.code == "VALIDATION_ERROR"
        assert exc.details["field"] == "email"

    def test_resource_not_found_formats_message(self):
        """Test ResourceNotFoundException formats message correctly."""
        from backend.core.exceptions import ResourceNotFoundException

        exc = ResourceNotFoundException("Patient", 123)

        assert exc.status_code == 404
        assert "Patient" in exc.message
        assert "123" in exc.message

    def test_rate_limit_exception_includes_retry_after(self):
        """Test RateLimitException includes retry info."""
        from backend.core.exceptions import RateLimitException

        exc = RateLimitException(retry_after=60)

        assert exc.status_code == 429
        assert exc.details["retry_after"] == 60


# ============================================
# HEALTH CHECK TESTS
# ============================================


class TestHealthChecks:
    """Tests for health check functions."""

    def test_basic_health_returns_healthy(self, client):
        """Test basic health endpoint returns healthy."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_liveness_probe_returns_alive(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/api/v1/health/live")

        assert response.status_code == 200
        assert response.json()["status"] == "alive"
