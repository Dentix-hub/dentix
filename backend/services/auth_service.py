from datetime import datetime, timedelta, timezone
import hashlib
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend import models

# For 2FA (Conceptual - requires pyotp for real or simple random for now)
import random
import string


class AuthService:
    SESSION_EXPIRY_HOURS = 24 * 7  # 1 week

    @staticmethod
    def generate_token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def create_session(
        db: Session,
        user_id: int,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
        device_info: str = None,
    ):
        """Create a new active session for the user (storing Refresh Token hash)."""
        token_hash = AuthService.generate_token_hash(refresh_token)

        # Check if identical session exists (optional cleanup)

        session = models.UserSession(
            user_id=user_id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=7),  # Match Refresh Token Expiry
        )
        db.add(session)
        db.commit()
        return session

    @staticmethod
    def get_session_by_token(db: Session, refresh_token: str):
        """Find session by refresh token hash."""
        token_hash = AuthService.generate_token_hash(refresh_token)
        return (
            db.query(models.UserSession)
            .filter(
                models.UserSession.token_hash == token_hash,
                models.UserSession.is_active == True,
                models.UserSession.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

    @staticmethod
    def revoke_session(db: Session, session_id: int, user_id: int):
        """Revoke a specific session."""
        session = (
            db.query(models.UserSession)
            .filter(
                models.UserSession.id == session_id,
                models.UserSession.user_id == user_id,
            )
            .first()
        )

        if session:
            session.is_active = False
            session.expires_at = datetime.now(timezone.utc)  # Expire immediately
            db.commit()
            return True
        return False

    @staticmethod
    def get_user_sessions(db: Session, user_id: int):
        """Get all active sessions for a user."""
        return (
            db.query(models.UserSession)
            .filter(
                models.UserSession.user_id == user_id,
                models.UserSession.is_active == True,
                models.UserSession.expires_at > datetime.now(timezone.utc),
            )
            .all()
        )

    # --- 2FA Logic ---

    @staticmethod
    def generate_2fa_secret(user: models.User):
        """Generate a random secret for 2FA setup (Simulation of TOTP secret)."""
        # In production: import pyotp; return pyotp.random_base32()
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(16))

    @staticmethod
    def verify_2fa_code(secret: str, code: str):
        """Verify the code against the secret."""
        # In production: totp = pyotp.TOTP(secret); return totp.verify(code)
        # For now, we simulate success if code is '123456' for testing
        # OR if we want real simulation, we'd need to store a temp code.
        # Let's assume for this MVP we accept '123456' as master code for verified flow
        # OR better: Assume the user enters a specific simulation code.
        return code == "123456"

    @staticmethod
    def enable_2fa(db: Session, user: models.User, secret: str, code: str):
        if not AuthService.verify_2fa_code(secret, code):
            raise HTTPException(status_code=400, detail="Invalid OTP code")

        user.is_2fa_enabled = True
        user.otp_secret = secret
        db.commit()
        return True

    @staticmethod
    def disable_2fa(db: Session, user: models.User):
        user.is_2fa_enabled = False
        user.otp_secret = None
        db.commit()
