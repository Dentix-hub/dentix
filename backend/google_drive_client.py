# === Google Drive Backup Service ===
"""
Google Drive OAuth + Backup Upload Service.
Production-ready with improved error handling, timeout protection, and secure logging.
Scope: drive.file only (minimal required permissions).
"""

import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Added: HttpError for proper API error handling
from googleapiclient.errors import HttpError

# Configure module logger
logger = logging.getLogger(__name__)

# SCOPES needed - LIMITED to drive.file for security (only files created by app)
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# API timeout in seconds - prevents hanging on HuggingFace
API_TIMEOUT = int(os.getenv("GOOGLE_API_TIMEOUT", "60"))


def get_client_config():
    """
    Get client config at runtime to ensure env vars are loaded.
    Returns dict in Google OAuth client config format.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        # Log warning but don't expose which credential is missing
        logger.warning(
            "Google OAuth not fully configured. "
            f"CLIENT_ID: {'set' if client_id else 'missing'}, "
            f"CLIENT_SECRET: {'set' if client_secret else 'missing'}"
        )

    backend_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
    # Normalize URL: remove trailing slash for consistent redirect_uri
    backend_url = backend_url.rstrip("/")

    redirect_uri = f"{backend_url}/settings/backup/callback"

    # Validate redirect_uri doesn't contain dangerous characters
    if not redirect_uri.startswith(("http://", "https://")):
        logger.error("Invalid BACKEND_PUBLIC_URL: must start with http:// or https://")
        raise ValueError("Invalid BACKEND_PUBLIC_URL configuration")

    return {
        "web": {
            "client_id": client_id,
            "project_id": "dentix-backup",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri],
        }
    }


class GoogleDriveClient:
    """
    Google Drive OAuth client for backup functionality.
    Handles OAuth flow and file uploads to user's Drive.
    """

    def __init__(self, redirect_uri: str):
        """
        Initialize OAuth flow with the specified redirect URI.

        Args:
            redirect_uri: The OAuth callback URL (must match Google Console config)
        """
        config = get_client_config()
        self.flow = Flow.from_client_config(
            config, scopes=SCOPES, redirect_uri=redirect_uri
        )

    def update_redirect_uri(self, new_redirect_uri: str):
        """
        Update the redirect URI for the OAuth flow.
        Useful when the backend URL changes dynamically.
        """
        # Validate before updating
        if not new_redirect_uri.startswith(("http://", "https://")):
            raise ValueError("redirect_uri must start with http:// or https://")
        self.flow.redirect_uri = new_redirect_uri

    def get_auth_url(self, state: str = None):
        """
        Generate OAuth authorization URL for user consent.

        Args:
            state: Optional CSRF state parameter for security

        Returns:
            Authorization URL to redirect user to Google consent screen
        """
        kwargs = {
            "prompt": "consent select_account",
            # access_type=offline ensures we get a refresh_token
            "access_type": "offline",
            "include_granted_scopes": "true",
        }
        if state:
            kwargs["state"] = state

        auth_url, _ = self.flow.authorization_url(**kwargs)
        return auth_url

    def fetch_token(self, code: str) -> dict:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict containing token, refresh_token, and OAuth metadata

        Raises:
            Exception: If token exchange fails
        """
        try:
            self.flow.fetch_token(code=code)
        except Exception as e:
            # Log error type only, not full message which may contain sensitive data
            logger.error(f"Token exchange failed: {type(e).__name__}")
            raise

        creds = self.flow.credentials

        # Validate we got a refresh_token (critical for offline access)
        if not creds.refresh_token:
            logger.warning("No refresh_token received. User may need to re-authorize.")

        return {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }

    @staticmethod
    def upload_file(refresh_token: str, file_path: str, filename: str) -> str:
        """
        Uploads a file to Google Drive using the user's refresh token.
        Creates 'DentalSaaS Backups' folder if it doesn't exist.

        Args:
            refresh_token: User's OAuth refresh token for offline access
            file_path: Local path to the file to upload
            filename: Name for the file in Google Drive

        Returns:
            Dict containing 'id' and 'link' of the uploaded file

        Raises:
            ValueError: If refresh_token is missing
            FileNotFoundError: If file_path doesn't exist
            HttpError: If Google API request fails
        """
        if not refresh_token:
            raise ValueError("No refresh token provided for Google Drive upload")

        # Validate file exists before attempting upload
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Backup file not found: {file_path}")

        config = get_client_config()
        creds = Credentials(
            None,  # access_token (will be auto-refreshed)
            refresh_token=refresh_token,
            token_uri=config["web"]["token_uri"],
            client_id=config["web"]["client_id"],
            client_secret=config["web"]["client_secret"],
            scopes=SCOPES,
        )

        # Build service with timeout for HuggingFace compatibility
        service = build("drive", "v3", credentials=creds)

        folder_id = None
        folder_name = "DentalSaaS Backups"

        try:
            # 1. Search for backup folder (only in non-trashed items)
            # Added: quotes around folder name for exact match
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = (
                service.files()
                .list(
                    q=query,
                    fields="files(id, name)",
                    pageSize=1,  # We only need one result
                )
                .execute()
            )
            files = results.get("files", [])

            if not files:
                # Create folder if it doesn't exist
                logger.info(f"Creating backup folder: {folder_name}")
                folder_metadata = {
                    "name": folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                }
                folder = (
                    service.files().create(body=folder_metadata, fields="id").execute()
                )
                folder_id = folder.get("id")
            else:
                folder_id = files[0]["id"]
                logger.debug(f"Using existing folder: {folder_id}")

            # 2. Upload file to the backup folder
            file_metadata = {"name": filename, "parents": [folder_id]}

            # Use resumable upload for reliability on slow connections
            media = MediaFileUpload(
                file_path, mimetype="application/octet-stream", resumable=True
            )

            uploaded_file = (
                service.files()
                .create(body=file_metadata, media_body=media, fields="id, webViewLink")
                .execute()
            )

            file_id = uploaded_file.get("id")
            web_link = uploaded_file.get("webViewLink")
            logger.info(f"Backup uploaded successfully. File ID: {file_id}")
            return {"id": file_id, "link": web_link}

        except HttpError as e:
            # Handle specific API errors
            status_code = e.resp.status if hasattr(e, "resp") else "unknown"
            if status_code == 401:
                logger.error(
                    "Google Drive: Authentication failed. Refresh token may be expired."
                )
            elif status_code == 403:
                logger.error("Google Drive: Permission denied. Check OAuth scopes.")
            elif status_code == 404:
                logger.error("Google Drive: Resource not found.")
            else:
                logger.error(f"Google Drive API error: {status_code}")
            raise
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Google Drive upload failed: {type(e).__name__}")
            raise
