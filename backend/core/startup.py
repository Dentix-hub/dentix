import os
import logging
from backend import google_drive_client
from backend.core.config import API_V1_STR

logger = logging.getLogger(__name__)

# Global instances
drive_client = None

def init_drive_client():
    """Build and return the Google Drive client instance."""
    global drive_client
    try:
        backend_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
        if backend_url.endswith("/"):
            backend_url = backend_url[:-1]

        drive_client = google_drive_client.GoogleDriveClient(
            redirect_uri=f"{backend_url}{API_V1_STR}/settings/backup/callback"
        )
        logger.info("[STARTUP] Google Drive Client Initialized.")
    except Exception as e:
        logger.warning("[STARTUP] Could not initialize Google Drive Client: %s", e)

        class MockDriveClient:
            def update_redirect_uri(self, *args): pass
            def get_auth_url(self, *args): return "#"
            def fetch_token(self, *args): raise Exception("Google Drive not configured")

        drive_client = MockDriveClient()
    return drive_client

def run_startup_patches():
    """Run any schema patches or data fixes required on startup."""
    # This matches the call already in main.py lifespan
    logger.info("[STARTUP] Running startup patches (place-holder)...")
    pass

# Initialize on module load if needed, but better to call init explicitly in main.py
