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
        *,
        commit: bool = True,
    ):
        """Create a new active device session, storing only the refresh-token hash."""
        token_hash = AuthService.generate_token_hash(refresh_token)

        session = models.UserSession(
            user_id=user_id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
            expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).replace(tzinfo=None),
        )
        db.add(session)
        if commit:
            await db.commit()
        else:
            await db.flush()
        return session

    @staticmethod
    async def get_session_by_token(
        db: AsyncSession,
        refresh_token: str,
        *,
        for_update: bool = False,
    ):
        """Find an active session by refresh-token hash."""
        token_hash = AuthService.generate_token_hash(refresh_token)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = select(models.UserSession).where(
            models.UserSession.token_hash == token_hash,
            models.UserSession.is_active,
            models.UserSession.expires_at > now,
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_active_session_by_sid(db: AsyncSession, user_id: int, sid: str):
        """Resolve the active device session referenced by an access-token sid."""
        if not sid:
            return None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = select(models.UserSession).where(
            models.UserSession.user_id == user_id,
            models.UserSession.device_info == sid,
            models.UserSession.is_active,
            models.UserSession.expires_at > now,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def revoke_user_session_by_sid(
        db: AsyncSession,
        user_id: int,
        sid: str,
        *,
        commit: bool = True,
    ) -> bool:
        """Revoke one device session without affecting the user's other devices."""
        if not sid:
            return False
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = select(models.UserSession).where(
            models.UserSession.user_id == user_id,
            models.UserSession.device_info == sid,
            models.UserSession.is_active,
        )
        session = (await db.execute(stmt)).scalars().first()
        if not session:
            return False
        session.is_active = False
        session.expires_at = now
        if commit:
            await db.commit()
        else:
            await db.flush()
        return True

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

        # Keep the legacy marker for administrative/security audit compatibility.
        # Request authentication is enforced against UserSession rows, not this field.
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
        """Generate a random base32 secret for 2FA setup."""
        import pyotp
        return pyotp.random_base32()

    @staticmethod
    def verify_2fa_code(secret: str, code: str) -> bool:
        """Verify the TOTP code against the secret."""
        if not secret or not code:
            return False
        import pyotp
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(code))

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
