"""Encryption helpers for secrets stored outside encrypted ORM columns."""

from backend.core.security import DecryptionError, get_encryption_manager


GOOGLE_SUPER_ADMIN_TOKEN_KEY = "google_refresh_token_super_admin"
SENSITIVE_SYSTEM_SETTING_KEYS = frozenset({GOOGLE_SUPER_ADMIN_TOKEN_KEY})


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return value

    manager = get_encryption_manager()
    try:
        manager.decrypt(value, allow_plaintext_fallback=False)
        return value
    except DecryptionError:
        return manager.encrypt(value)


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return value
    return get_encryption_manager().decrypt(value, allow_plaintext_fallback=True)
