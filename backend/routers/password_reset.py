import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from backend.core.limiter import limiter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
from pydantic import BaseModel, EmailStr, Field

from .. import models, database
from ..email_service import send_password_reset_email
from ..auth import get_password_hash
from .auth.dependencies import validate_password
from ..services.auth_service import AuthService
from ..services.auth_bootstrap import resolve_password_reset_identity, password_reset_identity_scope
from backend.core.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

from ..database import get_async_db

class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(..., description="New password")


@router.post(
    "/forgot-password",
    summary="Request password reset",
    description="Sends a password reset email. Rate limited to 5 requests/minute.",
)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Request password reset. Sends email with reset link.
    """
    message = "إذا كان البريد الإلكتروني موجوداً لدى النظام، ستصل رسالة لإعادة تعيين كلمة المرور"
    try:
        identity = await resolve_password_reset_identity(email=payload.email)
        if identity is None:
            return success_response(message=message)
        async with password_reset_identity_scope(db, identity, for_update=True) as (scoped_db, user):
            if user is None or not user.email or user.email.lower() != payload.email.strip().lower():
                return success_response(message=message)
            # User lock serializes issuance with other issuances and token use.
            await scoped_db.execute(
                update(models.PasswordResetToken)
                .where(models.PasswordResetToken.user_id == user.id, models.PasswordResetToken.used.is_(False))
                .values(used=True)
            )
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).replace(tzinfo=None)
            scoped_db.add(models.PasswordResetToken(token=token_hash, user_id=user.id, expires_at=expires_at))
            from backend.core.security import get_encryption_manager
            from backend.services.event_service import event_service

            event = event_service.emit_event(
                scoped_db, event_type="auth.password_reset.requested", aggregate_type="password_reset",
                aggregate_id=str(user.id), tenant_id=user.tenant_id,
                payload={"encrypted_token": get_encryption_manager().encrypt(token)},
            )
            event.max_attempts = 4
            await scoped_db.commit()
    except Exception:
        await db.rollback()
        # No token, recipient, provider exception, or SMTP status is logged.
        logger.error("Password reset request could not be queued")
    return success_response(message=message)


@router.post(
    "/reset-password",
    summary="Reset password with token",
    description="Reset password using the token received via email. Rate limited to 5 requests/minute.",
)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Reset password using token from email.
    """
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    identity = await resolve_password_reset_identity(token_hash=token_hash)
    if identity is None:
        raise HTTPException(status_code=400, detail="رابط غير صحيح أو منتهي الصلاحية")

    # Lock the identity first, then the token. Issuance follows the same order,
    # so concurrent use cannot consume a token twice or race a new request.
    async with password_reset_identity_scope(db, identity, for_update=True) as (scoped_db, user):
        if user is None:
            raise HTTPException(status_code=400, detail="رابط غير صحيح أو منتهي الصلاحية")
        result = await scoped_db.execute(
            select(models.PasswordResetToken).where(
                models.PasswordResetToken.user_id == user.id,
                models.PasswordResetToken.token == token_hash,
            ).with_for_update()
        )
        reset_token = result.scalars().first()
        if reset_token is None or reset_token.used:
            raise HTTPException(status_code=400, detail="رابط غير صحيح أو منتهي الصلاحية")
        expires = reset_token.expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if not expires or datetime.now(timezone.utc) > expires:
            reset_token.used = True
            await scoped_db.commit()
            raise HTTPException(status_code=400, detail="انتهت صلاحية الرابط. يرجى طلب رابط جديد")
        validate_password(payload.new_password, username=user.username)
        user.hashed_password = get_password_hash(payload.new_password)
        await AuthService.revoke_all_user_sessions(scoped_db, user.id, commit=False)
        reset_token.used = True
        await scoped_db.commit()

    return success_response(message="تم تغيير كلمة المرور بنجاح. يرجى تسجيل الدخول من جديد")


@router.get("/verify-reset-token")
@limiter.limit("5/minute")
async def verify_reset_token(
    request: Request,
    token: str = Query(..., description="Reset token to verify"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Verify if a reset token is valid (for frontend validation before showing form).
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    identity = await resolve_password_reset_identity(token_hash=token_hash)
    if identity is None:
        return error_response(message="رابط غير صحيح", status_code=400, details={"valid": False})

    async with password_reset_identity_scope(db, identity) as (scoped_db, user):
        if user is None:
            return error_response(message="رابط غير صحيح", status_code=400, details={"valid": False})
        result = await scoped_db.execute(
            select(models.PasswordResetToken).where(
                models.PasswordResetToken.user_id == user.id,
                models.PasswordResetToken.token == token_hash,
                models.PasswordResetToken.used.is_(False),
            )
        )
        reset_token = result.scalars().first()
        if reset_token is None:
            return error_response(message="رابط غير صحيح", status_code=400, details={"valid": False})
        expires = reset_token.expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if not expires or datetime.now(timezone.utc) > expires:
            return error_response(message="انتهت صلاحية الرابط", status_code=400, details={"valid": False})
        return success_response(data={"valid": True}, message="الرابط صحيح")
