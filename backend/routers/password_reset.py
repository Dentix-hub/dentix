import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from backend.core.limiter import limiter
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

from .. import models, database
from ..email_service import send_password_reset_email
from ..core.firebase_client import firebase_client
from ..auth import get_password_hash
from .auth.dependencies import validate_password
from backend.core.response import success_response
import os

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


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
            message="Ø¥Ø°Ø§ ÙƒØ§Ù† Ø§Ù„Ø¨Ø±ÙŠØ¯ Ø§Ù„Ø¥Ù„ÙƒØªØ±ÙˆÙ†ÙŠ Ù…Ø³Ø¬Ù„Ø§Ù‹ Ù„Ø¯ÙŠÙ†Ø§ØŒ Ø³ØªØµÙ„Ùƒ Ø±Ø³Ø§Ù„Ø© Ù„Ø¥Ø¹Ø§Ø¯Ø© ØªØ¹ÙŠÙŠÙ† ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±"
        )

    # 1. Generate Firebase Reset Link
    firebase_link = firebase_client.generate_password_reset_link(email)

    if firebase_link:
        # Send via our email service with the Firebase link
        email_sent = send_password_reset_email(email, firebase_link, user.username, is_firebase_link=True)
        if email_sent:
            return success_response(
                message="ØªÙ… Ø¥Ø±Ø³Ø§Ù„ Ø±Ø§Ø¨Ø· Ø¥Ø¹Ø§Ø¯Ø© ØªØ¹ÙŠÙŠÙ† ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ± Ø¥Ù„Ù‰ Ø¨Ø±ÙŠØ¯Ùƒ Ø§Ù„Ø¥Ù„ÙƒØªØ±ÙˆÙ†ÙŠ Ø¹Ø¨Ø± Firebase"
            )

    # Fallback to legacy system if Firebase is not ready or fails
    logger.warning(f"Firebase link generation failed for {email}, falling back to legacy SMTP")

    # Legacy logic: save token to DB and send via SMTP
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    reset_token = models.PasswordResetToken(
        token=token,
        user_id=user.id,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()

    email_sent = send_password_reset_email(email, token, user.username)
    if email_sent:
        return success_response(message="ØªÙ… Ø¥Ø±Ø³Ø§Ù„ Ø±Ø§Ø¨Ø· Ø¥Ø¹Ø§Ø¯Ø© ØªØ¹ÙŠÙŠÙ† ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ± (Legacy SMTP)")

    raise HTTPException(status_code=500, detail="ÙØ´Ù„ Ø¥Ø±Ø³Ø§Ù„ Ø§Ù„Ø¨Ø±ÙŠØ¯ Ø§Ù„Ø¥Ù„ÙƒØªØ±ÙˆÙ†ÙŠ")


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
            models.PasswordResetToken.used == False,  # noqa: E712
        )
        .first()
    )

    if not reset_token:
        raise HTTPException(status_code=400, detail="Ø±Ø§Ø¨Ø· ØºÙŠØ± ØµØ§Ù„Ø­ Ø£Ùˆ Ù…Ù†ØªÙ‡ÙŠ Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ©")

    # Check expiration
    if datetime.utcnow() > reset_token.expires_at:
        reset_token.used = True
        db.commit()
        raise HTTPException(
            status_code=400, detail="Ø§Ù†ØªÙ‡Øª ØµÙ„Ø§Ø­ÙŠØ© Ø§Ù„Ø±Ø§Ø¨Ø·. ÙŠØ±Ø¬Ù‰ Ø·Ù„Ø¨ Ø±Ø§Ø¨Ø· Ø¬Ø¯ÙŠØ¯"
        )

    # Get user and update password
    user = db.query(models.User).filter(models.User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯")

    # Validate new password strength using central logic
    validate_password(new_password)

    # Update password
    user.hashed_password = get_password_hash(new_password)

    # Mark token as used
    reset_token.used = True

    db.commit()

    return success_response(
        message="ØªÙ… ØªØºÙŠÙŠØ± ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ± Ø¨Ù†Ø¬Ø§Ø­. ÙŠÙ…ÙƒÙ†Ùƒ Ø§Ù„Ø¢Ù† ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„"
    )


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
            models.PasswordResetToken.used == False,  # noqa: E712
        )
        .first()
    )

    if not reset_token:
        return success_response(
            success=False, data={"valid": False}, message="Ø±Ø§Ø¨Ø· ØºÙŠØ± ØµØ§Ù„Ø­"
        )

    if datetime.utcnow() > reset_token.expires_at:
        return success_response(
            success=False, data={"valid": False}, message="Ø§Ù†ØªÙ‡Øª ØµÙ„Ø§Ø­ÙŠØ© Ø§Ù„Ø±Ø§Ø¨Ø·"
        )

    return success_response(data={"valid": True}, message="Ø§Ù„Ø±Ø§Ø¨Ø· ØµØ§Ù„Ø­")
