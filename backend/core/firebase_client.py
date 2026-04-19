import os
import logging
import firebase_admin
from firebase_admin import credentials, auth, messaging, storage

logger = logging.getLogger("smart_clinic")

class FirebaseClient:
    _instance = None
    _app = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize Firebase Admin SDK."""
        if self._app:
            return

        cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")

        if not cred_json:
            logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON not set. Firebase features will be disabled.")
            return

        try:
            # Check if JSON is a file path or a raw JSON string
            if cred_json.startswith("{") and cred_json.endswith("}"):
                import json
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
            else:
                cred = credentials.Certificate(cred_json)

            self._app = firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name
            })
            logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")

    @property
    def is_ready(self):
        return self._app is not None

    def send_push_notification(self, token: str, title: str, body: str, data: dict = None):
        """Send FCM notification."""
        if not self.is_ready:
            return False

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
            logger.info(f"Successfully sent FCM message: {response}")
            return True
        except Exception as e:
            logger.error(f"FCM Sending Error: {e}")
            return False

    def generate_password_reset_link(self, email: str):
        """Generate a password reset link using Firebase Auth."""
        if not self.is_ready:
            return None

        try:
            # Generate link (valid for 1 hour by default)
            link = auth.generate_password_reset_link(email)
            return link
        except Exception as e:
            logger.error(f"Firebase Password Reset Link Error: {e}")
            return None

# Global Instance
firebase_client = FirebaseClient()
