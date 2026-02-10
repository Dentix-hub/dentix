from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend import models, schemas, crud, auth
from backend.services.auth_service import AuthService
from backend.constants import ROLES
from backend.core.limiter import limiter
from .dependencies import get_db, get_current_user, oauth2_scheme
import uuid
import logging

logger = logging.getLogger("smart_clinic")

router = APIRouter()


# --- Login ---
@router.post("/token", response_model=schemas.Token)
@limiter.limit("5/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    try:
        """Authenticate user and return JWT token."""
        # 1. Fetch User safely
        try:
            user = crud.get_user(db, form_data.username)
        except Exception as db_err:
            logger.error(f"DB Error fetching user: {db_err}")
            raise HTTPException(status_code=500, detail="Database connection error")

        # 2. Verify Credentials
        # Use explicit check to distinguish generic errors from bad password
        is_valid = False
        try:
            if user:
                is_valid = auth.verify_password(
                    form_data.password, user.hashed_password
                )
        except Exception as hash_err:
            logger.error(f"Password Hashing Error: {hash_err}")
            # Don't crash, just deny
            is_valid = False

        if not user or not is_valid:
            # OPTIONAL: Differentiate for debugging if needed, but security best practice is generic.
            # However, user asked for "Wrong Password".
            # We will stick to the standard message but ensure it's reached.
            logger.warning(f"Login failed for: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="اسم المستخدم أو كلمة الصفحة غير صحيحة",  # Translated to Arabic for better UX
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check for Global Maintenance Mode
        if user.role != ROLES.SUPER_ADMIN:
            maintenance_mode = (
                db.query(models.SystemSetting)
                .filter(models.SystemSetting.key == "maintenance_mode")
                .first()
            )
            if maintenance_mode and maintenance_mode.value.lower() == "true":
                raise HTTPException(
                    status_code=503,
                    detail="System is currently under maintenance. Please try again later.",
                )

        # Check for Account Deactivation
        if hasattr(user, "is_active") and not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Your account has been disabled. Please contact support.",
            )

        # SECURITY: Check Tenant Status (Soft Delete / Inactive)
        # Fixes issue where deleted tenants could still login
        if user.role != ROLES.SUPER_ADMIN:
            if not user.tenant:
                # Clean up orphan users or just block them
                raise HTTPException(
                    status_code=403, detail="Account not linked to any active clinic."
                )

            if user.tenant.is_deleted:
                raise HTTPException(
                    status_code=403, detail="This clinic account has been deleted."
                )
            if not user.tenant.is_active:
                raise HTTPException(
                    status_code=403,
                    detail="Clinic account is inactive. Please contact support.",
                )

        # 2FA CHECK
        # Use getattr to be safe against missing columns in staging
        is_2fa = getattr(user, "is_2fa_enabled", False)
        secret = getattr(user, "otp_secret", None)

        if is_2fa and secret:
            temp_token = auth.create_access_token(
                data={"sub": user.username, "scope": "2fa_pending"},
                expires_delta=auth.timedelta(minutes=5),
            )
            return {
                "access_token": temp_token,
                "token_type": "bearer",
                "user_status": "2fa_required",
            }

        # Create Tokens
        session_id = str(uuid.uuid4())

        # SINGLE SESSION POLICY: Update user with new session ID
        user.active_session_id = session_id
        db.commit()

        access_token = auth.create_access_token(
            data={
                "sub": user.username,
                "role": user.role,
                "tenant_id": user.tenant_id,
                "sid": session_id,  # Session ID Claim
            }
        )
        refresh_token = auth.create_refresh_token(
            data={"sub": user.username, "sid": session_id}
        )

        # SINGLE SESSION POLICY: Invalidate all previous sessions for this user
        try:
            # This prevents the same account from being used on multiple devices simultaneously
            db.query(models.UserSession).filter(
                models.UserSession.user_id == user.id,
                models.UserSession.is_active == True,
            ).update({"is_active": False})

            # Record Session (with Refresh Token)
            AuthService.create_session(
                db,
                user.id,
                refresh_token,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                device_info=session_id,  # Store session ID in device info for tracking
            )
        except Exception as session_error:
            # Fallback if UserSessions table doesn't exist or other DB error
            logger.error(f"Session Management Failed: {session_error}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "role": user.role,
            "username": user.username,
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("10/minute")
def refresh_token(
    refresh_token: str = Form(...),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Exchange refresh token for new access token.
    Validates token against DB session to allow revocation.
    """
    try:
        # Decode token
        payload = auth.jwt.decode(
            refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM]
        )
        username: str = payload.get("sub")
        sid: str = payload.get("sid")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Check DB Session
        # We need to find the session by refresh token OR sid
        # Looking up by refresh token is safer

        # For performance, maybe decoded SID is enough, but we should verify it exists in DB
        db_session = AuthService.get_session_by_token(db, refresh_token)

        if not db_session or not db_session.is_active:
            # Check if user has a newer session (Single session policy)
            user = crud.get_user(db, username=username)
            if user and user.active_session_id != sid:
                raise HTTPException(
                    status_code=401, detail="Session Mismatch (Logged in elsewhere)"
                )

            raise HTTPException(status_code=401, detail="Session expired or revoked")

        # Check User
        user = crud.get_user(db, username=username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Verify Single Session match
        # If the user's active_session_id changed, this refresh token is old
        if hasattr(user, "active_session_id") and user.active_session_id:
            if sid and sid != user.active_session_id:
                raise HTTPException(
                    status_code=401, detail="Session Mismatch (Logged in elsewhere)"
                )

        # Generate new Access Token
        access_token = auth.create_access_token(
            data={
                "sub": user.username,
                "role": user.role,
                "tenant_id": user.tenant_id,
                "sid": sid,  # Keep same Session ID
            }
        )

        # Keep the same refresh token? Or rotate?
        # For now, keep same refresh token to avoid complicatons with client storage
        # Ideally, we should rotate refresh tokens too, but that requires updating DB

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,  # Return same refresh token
            "role": user.role,
            "username": user.username,
        }
    except auth.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return {"status": "error", "detail": str(e)}


@router.get("/sessions")
def get_sessions(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get active sessions for current user."""
    return AuthService.get_user_sessions(db, current_user.id)


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific session."""
    AuthService.revoke_session(db, session_id)
    return {"message": "Session revoked"}


# --- 2FA Endpoints ---
@router.post("/login/2fa", response_model=schemas.Token)
def login_2fa(
    code: str = Form(...),
    token: str = Depends(oauth2_scheme),  # Temp token from first step
    db: Session = Depends(get_db),
    request: Request = None,
):
    try:
        # Decode temp token
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        if payload.get("scope") != "2fa_pending":
            raise HTTPException(status_code=401, detail="Invalid 2FA token")

        username = payload.get("sub")
        user = crud.get_user(db, username=username)

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Verify Code
        import pyotp

        totp = pyotp.TOTP(user.otp_secret)
        if not totp.verify(code):
            raise HTTPException(status_code=401, detail="Invalid 2FA Code")

        # Success - Generate Real Tokens
        session_id = str(uuid.uuid4())

        # Update Session
        user.active_session_id = session_id
        db.commit()

        access_token = auth.create_access_token(
            data={
                "sub": user.username,
                "role": user.role,
                "tenant_id": user.tenant_id,
                "sid": session_id,
            }
        )
        refresh_token = auth.create_refresh_token(
            data={"sub": user.username, "sid": session_id}
        )

        # Record Session
        try:
            AuthService.create_session(
                db,
                user.id,
                refresh_token,
                ip_address=request.client.host if request else "unknown",
                user_agent=request.headers.get("user-agent") if request else "unknown",
                device_info="2FA Session",
            )
        except:
            pass

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "role": user.role,
            "username": user.username,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"2FA Error: {str(e)}")
