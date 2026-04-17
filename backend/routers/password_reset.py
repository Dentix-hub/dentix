"""
Password Reset Router
Handles forgot password and reset password endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from backend.core.limiter import limiter
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

from .. import models, database
from ..email_service import send_password_reset_email
from ..auth import get_password_hash
from .auth.dependencies import validate_password
from backend.core.response import success_response
import os


router = APIRouter(prefix="/auth", tags=["Authentication"])


from ..database import get_db


@router.post(
    "/forgot-password",
    summary="Request password reset",
    description="Sends a password reset email. Rate limited to 5 requests/minute.",
)
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    email: str = Query(..., description="User email address"),
    db: Session = Depends(get_db),
):
    """
    Request password reset. Sends email with reset link.
    """
    # Find user by email
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        # Don't reveal if email exists or not (security)
        return success_response(
            message="إذا كان البريد الإلكتروني مسجلاً لدينا، ستصلك رسالة لإعادة تعيين كلمة المرور"
        )

    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    # Invalidate any existing tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        not models.PasswordResetToken.used,
    ).update({"used": True})

    # Create new token
    reset_token = models.PasswordResetToken(
        token=token, user_id=user.id, expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()

    # Send email
    email_sent = send_password_reset_email(email, token, user.username)

    if not email_sent:
        # Only return token in development (NEVER in production)
        if os.getenv("ENVIRONMENT") == "production":
            return success_response(
                message="إذا كان البريد الإلكتروني مسجلاً لدينا، ستصلك رسالة لإعادة تعيين كلمة المرور"
            )
        # Development only - for testing without SMTP
        return success_response(
            data={"dev_token": token},
            message="تم إنشاء رابط إعادة التعيين (SMTP غير مُفعّل). في بيئة الإنتاج، سيُرسل الرابط للبريد الإلكتروني",
        )

    return success_response(message="تم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني")


@router.post(
    "/reset-password",
    summary="Reset password with token",
    description="Reset password using the token received via email. Rate limited to 5 requests/minute.",
)
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    token: str = Query(..., description="Reset token from email"),
    new_password: str = Query(..., description="New password"),
    db: Session = Depends(get_db),
):
    """
    Reset password using token from email.
    """
    # Find and validate token
    reset_token = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token == token,
            not models.PasswordResetToken.used,
        )
        .first()
    )

    if not reset_token:
        raise HTTPException(status_code=400, detail="رابط غير صالح أو منتهي الصلاحية")

    # Check expiration
    if datetime.utcnow() > reset_token.expires_at:
        reset_token.used = True
        db.commit()
        raise HTTPException(
            status_code=400, detail="انتهت صلاحية الرابط. يرجى طلب رابط جديد"
        )

    # Get user and update password
    user = db.query(models.User).filter(models.User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="المستخدم غير موجود")

    # Validate new password strength using central logic
    validate_password(new_password)

    # Update password
    user.hashed_password = get_password_hash(new_password)

    # Mark token as used
    reset_token.used = True

    db.commit()

    return success_response(message="تم تغيير كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول")


@router.get("/verify-reset-token")
def verify_reset_token(
    token: str = Query(..., description="Reset token to verify"),
    db: Session = Depends(get_db),
):
    """
    Verify if a reset token is valid (for frontend validation before showing form).
    """
    reset_token = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token == token,
            not models.PasswordResetToken.used,
        )
        .first()
    )

    if not reset_token:
        return success_response(success=False, data={"valid": False}, message="رابط غير صالح")

    if datetime.utcnow() > reset_token.expires_at:
        return success_response(success=False, data={"valid": False}, message="انتهت صلاحية الرابط")

    return success_response(data={"valid": True}, message="الرابط صالح")
