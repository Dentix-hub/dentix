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
from ..core.firebase_client import firebase_client
from ..auth import get_password_hash
from .auth.dependencies import validate_password
from ..services.auth_service import AuthService
from backend.core.response import success_response, error_response
import os

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
    email = payload.email
    # Find user by email
    result = await db.execute(select(models.User).filter(models.User.email == email))
    user = result.scalars().first()

    if not user:
        # Don't reveal if email exists or not (security)
        return success_response(
            message="إذا كان البريد الإلكتروني موجوداً لدى النظام، ستصل رسالة لإعادة تعيين كلمة المرور"
        )

    # Invalidate previous tokens
    await db.execute(
        update(models.PasswordResetToken)
        .where(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.used == False,  # noqa: E712
        )
        .values(used=True)
    )

    # 1. Generate Firebase Reset Link
    firebase_link = firebase_client.generate_password_reset_link(email)
    email_sent = False

    if firebase_link:
        # Send via our email service with the Firebase link
        email_sent = send_password_reset_email(email, firebase_link, user.username, is_firebase_link=True)

    # Fallback to legacy system if Firebase is not ready or fails
    if not email_sent:
        logger.warning(f"Firebase link generation failed for {email}, falling back to legacy SMTP")

        # Legacy logic: save hashed token to DB and send raw token via SMTP
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        reset_token = models.PasswordResetToken(
            token=token_hash,
            user_id=user.id,
            expires_at=expires_at
        )
        db.add(reset_token)
        await db.commit()

        email_sent = send_password_reset_email(email, token, user.username)

    if email_sent:
        return success_response(
            message="إذا كان البريد الإلكتروني موجوداً لدى النظام، ستصل رسالة لإعادة تعيين كلمة المرور"
        )

    raise HTTPException(status_code=500, detail="فشل إرسال البريد الإلكتروني")


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
    token = payload.token
    new_password = payload.new_password

    # Find and validate token (using SHA-256 hash)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token == token_hash,
            models.PasswordResetToken.used == False,  # noqa: E712
        )
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(status_code=400, detail="رابط غير صحيح أو منتهي الصلاحية")

    # Check expiration
    now = datetime.now(timezone.utc)
    expires = reset_token.expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        reset_token.used = True
        await db.commit()
        raise HTTPException(
            status_code=400, detail="انتهت صلاحية الرابط. يرجى طلب رابط جديد"
        )

    # Get user and update password
    user_result = await db.execute(select(models.User).filter(models.User.id == reset_token.user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="المستخدم غير موجود")

    # Validate new password strength using central logic
    validate_password(new_password)

    # Update password
    user.hashed_password = get_password_hash(new_password)

    # REVOKE ALL SESSIONS: Force logout on all devices after password reset
    revoked_count = await AuthService.revoke_all_user_sessions(db, user.id)
    if revoked_count > 0:
        logger.info(f"Revoked {revoked_count} sessions for user {user.username} after password reset")

    # Mark token as used
    reset_token.used = True

    await db.commit()

    return success_response(
        message="تم تغيير كلمة المرور بنجاح. يرجى تسجيل الدخول من جديد"
    )


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
    result = await db.execute(
        select(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token == token_hash,
            models.PasswordResetToken.used == False,  # noqa: E712
        )
    )
    reset_token = result.scalars().first()

    if not reset_token:
        return error_response(
            message="رابط غير صحيح",
            status_code=400,
            details={"valid": False}
        )

    now = datetime.now(timezone.utc)
    expires = reset_token.expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        return error_response(
            message="انتهت صلاحية الرابط",
            status_code=400,
            details={"valid": False}
        )

    return success_response(data={"valid": True}, message="الرابط صحيح")
