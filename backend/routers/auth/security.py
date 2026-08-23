from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas
from .dependencies import get_async_db, get_current_user
from backend.services.auth_service import AuthService
import pyotp
import qrcode
import io
import base64

router = APIRouter()


# --- 2FA Setup ---
# NOTE: no "/auth" segment here — main.py already mounts this router under
# f"{API_V1_STR}/auth". Duplicating it produced /api/v1/auth/auth/2fa/*.
@router.post("/2fa/setup")
async def setup_2fa(
    current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)
):
    """Generate a secret for 2FA setup."""
    # Generate Secret
    secret = pyotp.random_base32()

    # Save temp secret (don't enable yet)
    current_user.otp_secret = secret
    await db.commit()

    # Generate QR Code
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email, issuer_name="Smart Clinic"
    )

    img = qrcode.make(otp_uri)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return {"secret": secret, "qr_code": img_str, "otp_uri": otp_uri}


@router.post("/2fa/verify")
async def verify_2fa_setup(
    payload: schemas.TwoFactorVerifyRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Confirm 2FA setup with a code (JSON body)."""
    totp = pyotp.TOTP(payload.secret)
    if not totp.verify(payload.code):
        raise HTTPException(status_code=400, detail="Invalid Code")

    # Enable 2FA
    current_user.is_2fa_enabled = True
    current_user.otp_secret = payload.secret  # Persist if not already

    # REVOKE ALL SESSIONS when 2FA is enabled (security best practice)
    revoked_count = await AuthService.revoke_all_user_sessions(db, current_user.id)
    if revoked_count > 0:
        import logging
        logger = logging.getLogger("smart_clinic")
        logger.info(f"Revoked {revoked_count} sessions for user {current_user.username} after 2FA enable")

    await db.commit()

    return {"message": "2FA Enabled Successfully"}


@router.delete("/2fa/disable")
async def disable_2fa(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Disable 2FA for the current user."""
    current_user.is_2fa_enabled = False
    current_user.otp_secret = None

    # REVOKE ALL SESSIONS when 2FA is disabled (security best practice)
    revoked_count = await AuthService.revoke_all_user_sessions(db, current_user.id)
    if revoked_count > 0:
        import logging
        logger = logging.getLogger("smart_clinic")
        logger.info(f"Revoked {revoked_count} sessions for user {current_user.username} after 2FA disable")

    await db.commit()
    return {"message": "2FA Disabled Successfully"}
