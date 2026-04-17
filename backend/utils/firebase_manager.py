import firebase_admin
from firebase_admin import credentials, messaging
import logging
import os
import json

logger = logging.getLogger(__name__)

class FirebaseManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize Firebase Admin SDK."""
        if self._initialized:
            return

        try:
            # 1. Try to load from environment variable (JSON string)
            cert_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
            if cert_json:
                cert_dict = json.loads(cert_json)
                cred = credentials.Certificate(cert_dict)
            else:
                # 2. Try to load from file path
                cert_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-service-account.json")
                if os.path.exists(cert_path):
                    cred = credentials.Certificate(cert_path)
                else:
                    logger.warning("Firebase credentials not found. Push notifications will be disabled.")
                    return

            firebase_admin.initialize_app(cred)
            self._initialized = True
            logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

    def send_push_notification(self, token: str, title: str, body: str, data: dict = None):
        """Send a push notification to a specific device token."""
        if not self._initialized:
            logger.error("Firebase not initialized. Cannot send notification.")
            return None

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"Successfully sent push notification: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return None

# Global instance
firebase_manager = FirebaseManager()
