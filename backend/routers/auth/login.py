import os
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Response, Cookie, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models, schemas, crud, auth
from backend.services.auth_service import AuthService
from backend.core.permissions import Role
from backend.core.limiter import limiter
from .dependencies import (
    get_async_db,
    get_current_user,
    get_token_from_header_or_cookie,
    oauth2_scheme,
)
from backend.services.auth_bootstrap import (
    lookup_user_for_authentication,
    post_auth_write_scope,
    REASON_LOGIN,
    REASON_REFRESH,
)
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
# Non-sensitive readable hint used only to decide whether a PWA cold start
# should contact the auth backend. The httpOnly refresh cookie remains the
# authoritative credential and cannot be inspected from JavaScript.
_SESSION_HINT_COOKIE_NAME = "dentix_session_hint"


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
    """Set httpOnly auth cookies plus a non-sensitive PWA session hint."""
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
        response.set_cookie(
            key=_SESSION_HINT_COOKIE_NAME,
            value="1",
            httponly=False,
            secure=_COOKIE_SECURE,
            samesite=_COOKIE_SAMESITE,
            path="/",
            max_age=7 * 24 * 60 * 60,  # mirrors refresh session lifetime
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
        # HIGH-RLS-01: no tenant context exists before authentication, so the
        # identity lookup runs through the audited bootstrap path instead of a
        # contextless (RLS-invisible) SELECT.
        try:
            user = await lookup_user_for_authentication(
                db, form_data.username, reason=REASON_LOGIN
            )
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
                async with post_auth_write_scope(db, user) as scoped_db:
                    user.account_locked_until = None
                    user.failed_login_attempts = 0
                    await scoped_db.commit()

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
                async with post_auth_write_scope(db, user) as scoped_db:
                    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                    if user.failed_login_attempts >= 5:
                        user.account_locked_until = (datetime.now(timezone.utc) + timedelta(minutes=15)).replace(tzinfo=None)
                    await scoped_db.commit()

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

        # Create a device-scoped session. Logging in on another device no longer
        # revokes this device; security-wide actions still use revoke_all_user_sessions.
        session_id = str(uuid.uuid4())

        async with post_auth_write_scope(db, user) as scoped_db:
            user.failed_login_attempts = 0
            user.account_locked_until = None
            await scoped_db.commit()

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

        try:
            await AuthService.create_session(
                db,
                user.id,
                refresh_token,
                ip_address=_request_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                device_info=session_id,
            )
        except Exception as session_error:
            await db.rollback()
            logger.error("Session Management Failed: %s", session_error, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to create a secure session. Please try again.",
            )

        from fastapi.responses import JSONResponse
        # Mobile contract (HIGH-07): tokens are ALSO returned in the body so
        # native clients can use the Bearer flow; the web client keeps using
        # the httpOnly cookies set below and ignores these fields.
        res = JSONResponse(content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "role": user.role,
            "username": user.username,
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
    Validates token against the device's DB session to allow revocation.
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

        if username is None or not sid:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Authentication bootstrap performs an audited commit and therefore must
        # happen BEFORE acquiring the refresh-session row lock. Otherwise that
        # commit would release the lock and re-open the rotation race.
        user = await lookup_user_for_authentication(db, username, reason=REASON_REFRESH)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Lock the exact refresh-session row only after the bootstrap transaction
        # has finished. Concurrent refresh attempts for the same token now serialize.
        db_session = await AuthService.get_session_by_token(
            db, effective_refresh_token, for_update=True
        )
        if not db_session or not db_session.is_active:
            raise HTTPException(status_code=401, detail="Session expired or revoked")
        if db_session.user_id != user.id or db_session.device_info != sid:
            raise HTTPException(status_code=401, detail="Invalid refresh session")

        # Generate new Access Token
        access_token = auth.create_access_token(
            data={
                "sub": user.username,
                "role": user.role,
                "tenant_id": user.tenant_id,
                "sid": sid,
            }
        )

        # REFRESH TOKEN ROTATION — old-row revoke and new-row creation are one
        # transaction. We never hand the client a token that failed to persist.
        new_refresh_token = auth.create_refresh_token(
            data={"sub": user.username, "sid": sid}
        )
        try:
            db_session.is_active = False
            await AuthService.create_session(
                db,
                user.id,
                new_refresh_token,
                ip_address=_request_client_ip(request),
                user_agent=request.headers.get("user-agent") if request else None,
                device_info=sid,
                commit=False,
            )
            await db.commit()
        except Exception as rotation_error:
            await db.rollback()
            logger.error("Failed to rotate refresh session: %s", rotation_error, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to refresh session. Please try again.",
            )

        from fastapi.responses import JSONResponse
        # Mobile contract (HIGH-07): rotated tokens are ALSO returned in the
        # body for native Bearer clients; the web keeps using cookies.
        res = JSONResponse(content={
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "role": user.role,
            "username": user.username,
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
    token: str | None = Depends(get_token_from_header_or_cookie),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Revoke only the current device session and clear its auth cookies."""
    sid = None
    if token:
        try:
            payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            sid = payload.get("sid")
        except auth.JWTError:
            sid = None

    if sid:
        await AuthService.revoke_user_session_by_sid(db, current_user.id, sid)
    else:
        # Legacy access tokens without sid cannot be mapped safely to one device.
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
    # Clear readable session hint and CSRF token cookies.
    response.delete_cookie(
        key=_SESSION_HINT_COOKIE_NAME,
        path="/",
        httponly=False,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
    )
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

        # Record this 2FA-authenticated device session without revoking others.
        try:
            await AuthService.create_session(
                db,
                user.id,
                refresh_token,
                ip_address=_request_client_ip(request) or "unknown",
                user_agent=request.headers.get("user-agent") if request else "unknown",
                device_info=session_id,
            )
        except Exception as session_error:
            await db.rollback()
            logger.error("2FA session persistence failed: %s", session_error, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to create a secure session. Please try again.",
            )

        from fastapi.responses import JSONResponse
        res = JSONResponse(content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "role": user.role,
            "username": user.username,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("2FA Error for user %s: %s", payload.get("sub") if 'payload' in locals() else "unknown", e, exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid 2FA code or session expired")
