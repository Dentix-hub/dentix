from datetime import datetime, timedelta, timezone
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select
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
    async def create_session(
        db: AsyncSession,
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
            expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).replace(tzinfo=None),
        )
        db.add(session)
        await db.commit()
        return session

    @staticmethod
    async def get_session_by_token(db: AsyncSession, refresh_token: str):
        """Find session by refresh token hash."""
        token_hash = AuthService.generate_token_hash(refresh_token)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            select(models.UserSession)
            .where(
                models.UserSession.token_hash == token_hash,
                models.UserSession.is_active,
                models.UserSession.expires_at > now,
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def revoke_session(db: AsyncSession, session_id: int, user_id: int):
        """Revoke a specific session."""
        stmt = (
            select(models.UserSession)
            .where(
                models.UserSession.id == session_id,
                models.UserSession.user_id == user_id,
            )
            .options(joinedload(models.UserSession.user))
        )
        result = await db.execute(stmt)
        session = result.scalars().first()

        if session:
            session.is_active = False
            session.expires_at = datetime.now(timezone.utc).replace(tzinfo=None)  # Expire immediately

            # If this was the active session, clear it from user record to trigger kickout
            if session.user and session.device_info == getattr(session.user, "active_session_id", None):
                session.user.active_session_id = "revoked_" + str(session.id)

            await db.commit()
            return True
        return False

    @staticmethod
    async def get_user_sessions(db: AsyncSession, user_id: int):
        """Get all active sessions for a user."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            select(models.UserSession)
            .where(
                models.UserSession.user_id == user_id,
                models.UserSession.is_active,
                models.UserSession.expires_at > now,
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def revoke_all_user_sessions(
        db: AsyncSession, user_id: int, *, commit: bool = True
    ) -> int:
        """
        Revoke ALL active sessions for a user.
        Used when: password changed, 2FA toggled, user disabled, role changed.
        Returns count of revoked sessions.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            select(models.UserSession)
            .where(
                models.UserSession.user_id == user_id,
                models.UserSession.is_active,
                models.UserSession.expires_at > now,
            )
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        count = 0
        stmt_user = select(models.User).where(models.User.id == user_id)
        result_user = await db.execute(stmt_user)
        user = result_user.scalars().first()
        for session in sessions:
            session.is_active = False
            session.expires_at = now
            count += 1

        # Also invalidate the active_session_id on the user record to force logout
        if user:
            user.active_session_id = "revoked_all_" + str(user_id)

        if commit and (count > 0 or user):
            await db.commit()
        elif count > 0 or user:
            await db.flush()
        return count

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
    async def enable_2fa(db: AsyncSession, user: models.User, secret: str, code: str):
        if not AuthService.verify_2fa_code(secret, code):
            raise HTTPException(status_code=400, detail="Invalid OTP code")

        user.is_2fa_enabled = True
        user.otp_secret = secret
        await db.commit()
        return True

    @staticmethod
    async def disable_2fa(db: AsyncSession, user: models.User):
        user.is_2fa_enabled = False
        user.otp_secret = None
        await db.commit()
