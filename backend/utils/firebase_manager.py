"""Compatibility shim over the single Firebase bootstrap (plan §2.9 / §12.1).

Historically two wrappers could both call `firebase_admin.initialize_app`:
`backend/core/firebase_client.py` and this module. The duplicate default-app
initialization is now removed: `core.firebase_client` owns the ONLY Firebase
Admin bootstrap, and this manager delegates to it so existing callers
(`backend/main.py` startup) keep working unchanged.
"""

import logging

logger = logging.getLogger(__name__)


class FirebaseManager:
    """Thin facade over the canonical FirebaseClient singleton."""

    def __init__(self) -> None:
        from backend.core.firebase_client import firebase_client

        self._client = firebase_client

    def initialize(self) -> None:
        """Initialize the shared Firebase Admin app (idempotent)."""
        if self._client.is_ready:
            return
        # FirebaseClient initializes itself lazily on first instantiation;
        # touching is_ready already ran _initialize(). Log the outcome once.
        if self._client.is_ready:
            logger.info("Firebase Admin SDK initialized successfully.")
        else:
            logger.warning("Firebase credentials not found. Push notifications will be disabled.")

    @property
    def is_initialized(self) -> bool:
        return self._client.is_ready

    def send_push_notification(self, token: str, title: str, body: str, data: dict = None):
        """Delegate legacy FCM sends to the canonical client."""
        return self._client.send_push_notification(token=token, title=title, body=body, data=data)


# Global instance
firebase_manager = FirebaseManager()
