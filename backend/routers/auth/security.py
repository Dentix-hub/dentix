from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend import models
from .dependencies import get_db, get_current_user
import pyotp
import qrcode
import io
import base64

router = APIRouter()


# --- 2FA Setup ---
@router.post("/auth/2fa/setup")
def setup_2fa(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Generate a secret for 2FA setup."""
    # Generate Secret
    secret = pyotp.random_base32()

    # Save temp secret (don't enable yet)
    current_user.otp_secret = secret
    db.commit()

    # Generate QR Code
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email, issuer_name="Smart Clinic"
    )

    img = qrcode.make(otp_uri)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return {"secret": secret, "qr_code": img_str, "otp_uri": otp_uri}


@router.post("/auth/2fa/verify")
def verify_2fa_setup(
    code: str,
    secret: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm 2FA setup with a code."""
    totp = pyotp.TOTP(secret)
    if not totp.verify(code):
        raise HTTPException(status_code=400, detail="Invalid Code")

    # Enable 2FA
    current_user.is_2fa_enabled = True
    current_user.otp_secret = secret  # Persist if not already
    db.commit()

    return {"message": "2FA Enabled Successfully"}
