import os
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Response, Cookie, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend import models, schemas, crud, auth
from backend.services.auth_service import AuthService
from backend.core.permissions import Role
from backend.core.limiter import limiter
from .dependencies import get_async_db, get_current_user, oauth2_scheme
import uuid
import logging
import secrets
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("smart_clinic")

router = APIRouter()

# Cookie security settings
_COOKIE_SECURE = os.getenv("ENVIRONMENT", "development").lower() == "production"
_COOKIE_SAMESITE = "lax"  # Lax is sufficient and safer for UX

# CSRF token cookie name (non-httpOnly so JS can read it)
_CSRF_COOKIE_NAME = "csrf_token"
_CSRF_HEADER_NAME = "X-CSRF-Token"

def _generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(32)

def _set_csrf_cookie(response: Response) -> str:
    """Set CSRF token cookie (readable by JavaScript for double-submit pattern)."""
    token = _generate_csrf_token()
    response.set_cookie(
        key=_CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # IMPORTANT: Must be readable by JavaScript
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path="/",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return token

def _get_csrf_token(request: Request) -> str | None:
    """Get CSRF token from cookie."""
    return request.cookies.get(_CSRF_COOKIE_NAME)

def _validate_csrf(request: Request, x_csrf_token: str | None = Header(None, alias="X-CSRF-Token")) -> bool:
    """Validate CSRF token using double-submit pattern."""
    cookie_token = request.cookies.get(_CSRF_COOKIE_NAME)
    if not cookie_token:
        return False

    # If called manually from middleware, x_csrf_token is a Header object instead of a string
    if not isinstance(x_csrf_token, str):
        x_csrf_token = request.headers.get("X-CSRF-Token")

    if not x_csrf_token:
        return False
    # Timing-safe comparison
    return secrets.compare_digest(cookie_token, x_csrf_token)

def require_csrf(request: Request, x_csrf_token: str | None = Header(None, alias="X-CSRF-Token")) -> None:
    """Dependency that raises 403 if CSRF validation fails."""
    if not _validate_csrf(request, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed"
        )

def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str | None = None
) -> None:
    """Set httpOnly cookies for JWT tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path="/",
        max_age=15 * 60,  # 15 minutes
    )
    if refresh_token:
        from backend.core.config import API_V1_STR
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=_COOKIE_SECURE,
            samesite=_COOKIE_SAMESITE,
            path=f"{API_V1_STR}/auth/refresh",  # restrict to refresh endpoint only
            max_age=7 * 24 * 60 * 60,  # 7 days
        )


def _request_client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


# --- Login ---
@router.post("/token", response_model=schemas.Token)
@limiter.limit("20/minute")
async def login_for_access_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    """Authenticate user and return JWT token."""
    try:
        # 1. Fetch User safely
        try:
            user = await crud.get_user(db, form_data.username)
        except Exception as db_err:
            logger.error(f"DB Error fetching user: {db_err}")
            raise HTTPException(status_code=500, detail="Database connection error")

        # 2. Check Lockout Status
        if user and user.account_locked_until:
            lockout_time = user.account_locked_until
            # DB stores naive datetimes; normalize before comparing with UTC-aware now
            if lockout_time.tzinfo is None:
                lockout_time = lockout_time.replace(tzinfo=timezone.utc)
            if lockout_time > datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=403,
                    detail="تم قفل الحساب مؤقتاً بسبب كثرة المحاولات الخاطئة. يرجى المحاولة بعد 15 دقيقة."
                )
            else:
                # Lockout expired, reset it
                user.account_locked_until = None
                user.failed_login_attempts = 0
                await db.commit()

        # 3. Verify Credentials
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
            logger.warning(f"Login failed for: {form_data.username} from IP {_request_client_ip(request)}")
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= 5:
                    user.account_locked_until = (datetime.now(timezone.utc) + timedelta(minutes=15)).replace(tzinfo=None)
                await db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="اسم المستخدم أو كلمة المرور غير صحيحة",  # Translated to Arabic for better UX
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check for Global Maintenance Mode
        if user.role != Role.SUPER_ADMIN.value:
            try:
                stmt_m = select(models.SystemSetting).where(models.SystemSetting.key == "maintenance_mode")
                result_m = await db.execute(stmt_m)
                maintenance_mode = result_m.scalars().first()
                if maintenance_mode and maintenance_mode.value.lower() == "true":
                    raise HTTPException(
                        status_code=503,
                        detail="System is currently under maintenance. Please try again later.",
                    )
            except HTTPException:
                raise
            except Exception:
                # If system_settings table is missing, skip maintenance check
                pass

        # Check for Account Deactivation
        if hasattr(user, "is_active") and not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Your account has been disabled. Please contact support.",
            )

        # SECURITY: Check Tenant Status (Soft Delete / Inactive)
        # Fixes issue where deleted tenants could still login
        if user.role != Role.SUPER_ADMIN.value:
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
                expires_delta=timedelta(minutes=5),
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
        user.failed_login_attempts = 0
        user.account_locked_until = None
        await db.commit()

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
            await db.execute(
                update(models.UserSession)
                .where(
                    models.UserSession.user_id == user.id,
                    models.UserSession.is_active == True,  # noqa: E712
                )
                .values(is_active=False)
            )

            # Record Session (with Refresh Token)
            await AuthService.create_session(
                db,
                user.id,
                refresh_token,
                ip_address=_request_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                device_info=session_id,  # Store session ID in device info for tracking
            )
        except Exception as session_error:
            # Fallback if UserSessions table doesn't exist or other DB error
            logger.error(f"Session Management Failed: {session_error}")

        from fastapi.responses import JSONResponse
        res = JSONResponse(content={
            "user": {
                "id": str(user.id),
                "name": user.full_name or user.username,
                "email": user.email,
                "role": user.role,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            },
            "session_id": session_id,
        })
        _set_auth_cookies(res, access_token, refresh_token)
        _set_csrf_cookie(res)
        return res
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit("10/minute")
async def refresh_token(
    response: Response,
    request: Request,
    refresh_token: str = Form(""),
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Exchange refresh token for new access token.
    Validates token against DB session to allow revocation.
    """
    try:
        # Prefer cookie over form data for refresh token
        effective_refresh_token = refresh_token or refresh_token_cookie
        if not effective_refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token missing")

        # Decode token
        payload = auth.jwt.decode(
            effective_refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM]
        )
        username: str = payload.get("sub")
        sid: str = payload.get("sid")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Check DB Session
        # We need to find the session by refresh token OR sid
        # Looking up by refresh token is safer

        # For performance, maybe decoded SID is enough, but we should verify it exists in DB
        db_session = await AuthService.get_session_by_token(db, effective_refresh_token)

        if not db_session or not db_session.is_active:
            # Check if user has a newer session (Single session policy)
            user = await crud.get_user(db, username=username)
            if user and user.active_session_id != sid:
                raise HTTPException(
                    status_code=401, detail="Session Mismatch (Logged in elsewhere)"
                )

            raise HTTPException(status_code=401, detail="Session expired or revoked")

        # Check User
        user = await crud.get_user(db, username=username)
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

        # REFRESH TOKEN ROTATION
        # 1. Invalidate old session
        db_session.is_active = False
        await db.commit()

        # 2. Generate new refresh token
        new_refresh_token = auth.create_refresh_token(
            data={"sub": user.username, "sid": sid}
        )

        # 3. Create new session DB record
        try:
            await AuthService.create_session(
                db,
                user.id,
                new_refresh_token,
                ip_address=_request_client_ip(request),
                user_agent=request.headers.get("user-agent") if request else None,
                device_info=db_session.device_info or sid,
            )
        except Exception as e:
            logger.error(f"Failed to save rotated session: {e}")

        from fastapi.responses import JSONResponse
        res = JSONResponse(content={
            "user": {
                "id": str(user.id),
                "name": user.full_name or user.username,
                "email": user.email,
                "role": user.role,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            },
            "session_id": sid,
        })
        _set_auth_cookies(res, access_token, new_refresh_token)
        _set_csrf_cookie(res)
        return res
    except HTTPException:
        raise
    except auth.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise e


@router.get("/session")
async def get_auth_session(
    current_user: models.User = Depends(get_current_user)
):
    """Get the current authenticated user's session details."""
    from backend.core.response import success_response
    return success_response(data={
        "id": current_user.id,
        "name": current_user.full_name or current_user.username,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
    })


@router.get("/sessions")
async def get_sessions(

    current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)
):
    """Get active sessions for current user."""
    return await AuthService.get_user_sessions(db, current_user.id)


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revoke a specific session."""
    await AuthService.revoke_session(db, session_id, current_user.id)
    return {"message": "Session revoked"}


@router.post("/logout")
async def logout(
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revoke the authenticated server session and clear auth cookies."""
    await AuthService.revoke_all_user_sessions(db, current_user.id)

    # Clear access_token cookie
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
    )
    # Clear refresh_token cookie
    from backend.core.config import API_V1_STR
    response.delete_cookie(
        key="refresh_token",
        path=f"{API_V1_STR}/auth/refresh",
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
    )
    # Clear CSRF token cookie
    response.delete_cookie(
        key=_CSRF_COOKIE_NAME,
        path="/",
        httponly=False,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
    )
    return {"message": "Logged out successfully"}


# --- 2FA Endpoints ---
@router.post("/login/2fa", response_model=schemas.Token)
@limiter.limit("5/minute")
async def login_2fa(
    response: Response,
    request: Request,
    code: str = Form(...),
    token: str = Depends(oauth2_scheme),  # Temp token from first step
    db: AsyncSession = Depends(get_async_db),
):
    try:
        # Decode temp token
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        if payload.get("scope") != "2fa_pending":
            raise HTTPException(status_code=401, detail="Invalid 2FA token")

        username = payload.get("sub")
        user = await crud.get_user(db, username=username)

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
        await db.commit()

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
            await AuthService.create_session(
                db,
                user.id,
                refresh_token,
                ip_address=_request_client_ip(request) or "unknown",
                user_agent=request.headers.get("user-agent") if request else "unknown",
                device_info="2FA Session",
            )
        except Exception:
            pass

        from fastapi.responses import JSONResponse
        res = JSONResponse(content={
            "user": {
                "id": str(user.id),
                "name": user.full_name or user.username,
                "email": user.email,
                "role": user.role,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            },
            "session_id": session_id,
        })
        _set_auth_cookies(res, access_token, refresh_token)
        _set_csrf_cookie(res)
        return res
    except Exception as e:
        logger.error("2FA Error for user %s: %s", payload.get("sub") if 'payload' in locals() else "unknown", e, exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid 2FA code or session expired")
