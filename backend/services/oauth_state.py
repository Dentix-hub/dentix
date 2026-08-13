"""Short-lived signed state values for external OAuth redirects."""

import secrets
from datetime import datetime, timedelta, timezone

from backend import auth


_PURPOSE = "google-drive-backup"


def create_backup_oauth_state(subject: str | int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "purpose": _PURPOSE,
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=10),
        "nonce": secrets.token_urlsafe(16),
    }
    return auth.jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)


def read_backup_oauth_state(state: str) -> str:
    try:
        payload = auth.jwt.decode(
            state, auth.SECRET_KEY, algorithms=[auth.ALGORITHM]
        )
    except Exception as exc:
        raise ValueError("Invalid or expired OAuth state") from exc

    if payload.get("purpose") != _PURPOSE or not payload.get("sub"):
        raise ValueError("Invalid OAuth state")
    return str(payload["sub"])
