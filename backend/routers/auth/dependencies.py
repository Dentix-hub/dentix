import logging
logger = logging.getLogger(__name__)
from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas, crud, auth
from backend.database import get_async_db
from backend.core.permissions import Role
from backend.services.auth_service import AuthService
from backend.services.entitlement_service import EntitlementService

# OAuth Scheme (for Swagger UI / OpenAPI docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Bearer scheme with auto_error=False to allow cookie fallback
bearer_scheme = HTTPBearer(auto_error=False)


SAFE_IMPERSONATION_METHODS = {"GET", "HEAD", "OPTIONS"}


def _enforce_impersonation_scope(payload: dict, request_method: str) -> None:
    """Enforce the scope embedded in temporary Super Admin impersonation tokens."""
    if not payload.get("is_impersonating"):
        return

    scope = payload.get("impersonation_scope")
    if scope not in {"read_only", "full_access"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid impersonation scope",
        )

    if scope == "read_only" and request_method.upper() not in SAFE_IMPERSONATION_METHODS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only impersonation cannot modify clinic data",
        )


def get_token_from_header_or_cookie(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    access_token: str | None = Cookie(None),
) -> str | None:
    """Extract JWT from Authorization header or httpOnly cookie."""
    if credentials:
        return credentials.credentials
    return access_token


PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 72

COMMON_WEAK_PASSWORDS: frozenset[str] = frozenset({
    # Numeric / sequential + letter patterns
    "12345678",
    "123456789",
    "1234567890",
    "1234567a",
    "12345678a",
    "123456789a",
    "a1234567",
    "a12345678",
    "a123456789",
    "12341234a",
    "11223344a",
    "123123123a",
    "87654321a",
    "0987654321a",
    # Repeated character + digit / letter patterns (11111111a1-style)
    "1111111a",
    "11111111",
    "11111111a",
    "11111111a1",
    "0000000a",
    "00000000",
    "00000000a",
    "00000000a0",
    "22222222a",
    "33333333a",
    "44444444a",
    "55555555a",
    "66666666a",
    "77777777a",
    "88888888a",
    "99999999a",
    "aaaaaaa1",
    "aaaaaaaa1",
    "aaaaaaaa1a",
    "bbbbbbb1",
    "zzzzzzz1",
    # Common password / keyboard walks
    "password",
    "password1",
    "password2",
    "password3",
    "password12",
    "password123",
    "password1234",
    "password12345",
    "password1!",
    "password123!",
    "passw0rd",
    "passw0rd1",
    "p@ssw0rd",
    "p@ssword1",
    "p4ssw0rd",
    "pass1234",
    "pass12345",
    "qwerty12",
    "qwerty123",
    "qwerty1234",
    "qwerty12345",
    "qwertyui1",
    "q1w2e3r4",
    "q1w2e3r4t5",
    "1q2w3e4r",
    "1q2w3e4r5t",
    "1qaz2wsx",
    "zaq12wsx",
    "asdf1234",
    "asdfgh12",
    "asdfghj1",
    "asdfghjk1",
    "zxcv1234",
    "zxcvbn12",
    "zxcvbnm1",
    "abcd1234",
    "abc123456",
    "abcdefg1",
    "abcdefgh1",
    # Admin / role / product / clinic weak defaults
    "admin123",
    "admin1234",
    "admin12345",
    "admin111",
    "admin1111",
    "admin0000",
    "admin2023",
    "admin2024",
    "admin2025",
    "admin2026",
    "administrator1",
    "root1234",
    "root12345",
    "user1234",
    "user12345",
    "test1234",
    "test12345",
    "testing1",
    "testing123",
    "guest123",
    "guest1234",
    "default1",
    "changeme1",
    "changeme123",
    "dentix12",
    "dentix123",
    "dentix1234",
    "dentix2024",
    "dentix2025",
    "dentix2026",
    "dental12",
    "dental123",
    "dental1234",
    "dentist1",
    "dentist123",
    "clinic12",
    "clinic123",
    "clinic1234",
    "doctor12",
    "doctor123",
    "doctor1234",
    "smartclinic1",
    "smart123",
    "smart1234",
    # Common English dictionary + digits
    "welcome1",
    "welcome12",
    "welcome123",
    "letmein1",
    "letmein12",
    "letmein123",
    "iloveyou1",
    "iloveyou2",
    "iloveyou123",
    "sunshine1",
    "princess1",
    "football1",
    "baseball1",
    "monkey12",
    "monkey123",
    "dragon12",
    "dragon123",
    "master12",
    "master123",
    "shadow12",
    "shadow123",
    "superman1",
    "batman12",
    "batman123",
    "trustno1",
    "whatever1",
    "freedom1",
    "starwars1",
    "mustang1",
    "michael1",
    "charlie1",
    "jessica1",
    # Common regional / transliterated weak passwords
    "egypt123",
    "egypt1234",
    "cairo123",
    "cairo1234",
    "allah123",
    "bismillah1",
    "mohamed1",
    "mohamed12",
    "mohamed123",
    "mahmoud1",
    "mahmoud123",
    "mostafa1",
    "mostafa123",
    "ibrahim1",
    "ibrahim123",
})


def validate_password(password: str, username: str | None = None) -> None:
    """
    Validate password strength using the relaxed policy:
    - Minimum length PASSWORD_MIN_LENGTH (8), maximum PASSWORD_MAX_LENGTH (72).
    - At least one letter (Arabic or Latin: str.isalpha()) and at least one digit.
    - Not equal to the username (case-insensitive / normalized).
    - Not in the common weak password blocklist (COMMON_WEAK_PASSWORDS).
    Raises HTTPException(400) if validation fails.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"كلمة المرور يجب أن تتكون من {PASSWORD_MIN_LENGTH} أحرف على الأقل",
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="كلمة المرور يجب أن لا تزيد عن 72 حرفاً",
        )

    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_letter and has_digit):
        raise HTTPException(
            status_code=400,
            detail="كلمة المرور يجب أن تحتوي على حروف وأرقام على الأقل",
        )

    if username and username.strip():
        clean_user = crud.normalize_username(username)
        clean_pass = crud.normalize_username(password)
        if (
            password.strip().lower() == username.strip().lower()
            or (clean_user and clean_pass == clean_user)
        ):
            raise HTTPException(
                status_code=400,
                detail="كلمة المرور ضعيفة: لا يمكن أن تكون مطابقة لاسم المستخدم",
            )

    if password.lower() in COMMON_WEAK_PASSWORDS:
        raise HTTPException(
            status_code=400,
            detail="كلمة المرور ضعيفة جداً وشائعة الاستخدام، يرجى اختيار كلمة مرور أخرى",
        )


async def get_current_user(
    request: Request,
    token: str | None = Depends(get_token_from_header_or_cookie),
    db: AsyncSession = Depends(get_async_db)
):
    """Validate JWT token and return current user."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        tenant_id: int = payload.get("tenant_id")
        if username is None or payload.get("scope") == "2fa_pending":
            raise credentials_exception
        _enforce_impersonation_scope(payload, request.method)
        token_data = schemas.TokenData(username=username, tenant_id=tenant_id)
    except HTTPException:
        raise
    except auth.JWTError:
        logger.debug("JWT error for user: %s", username if 'username' in locals() else "unknown")
        raise credentials_exception
    except Exception as e:
        logger.error("Unexpected authentication error: %s", e, exc_info=True)
        raise credentials_exception

    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from backend.core.tenancy import get_current_tenant_id
    from backend.services.auth_bootstrap import (
        lookup_user_for_authentication,
        REASON_SESSION_RESOLVE,
    )

    if get_current_tenant_id() is not None:
        # Tenant bound from the signed request token/cookie by middleware:
        # the identity read stays fully tenant-scoped (FORCE RLS enforced).
        stmt = select(models.User).where(models.User.username == token_data.username).options(joinedload(models.User.tenant).joinedload(models.Tenant.subscription_plan))
        result = await db.execute(stmt)
        user = result.scalars().first()
    else:
        # HIGH-RLS-01: no tenant could be bound from the request itself
        # (super-admin, or a contextless internal path). Resolve identity via
        # the audited bootstrap scope; every other row stays invisible. The
        # helper also re-binds the session/process to the resolved tenant.
        user = await lookup_user_for_authentication(
            db, token_data.username, reason=REASON_SESSION_RESOLVE
        )
    if user is None:
        logger.debug("User not found in DB for authenticated username: %s", token_data.username)
        raise credentials_exception

    # Make verified audit identity available before any subsequent session,
    # subscription, or RBAC rejection is converted into an HTTP response.
    request.state.error_log_identity = (user.id, user.tenant_id)

    # Device-scoped session enforcement. A login on another device must not
    # invalidate this access token; only revoking this token's own sid (or a
    # security-wide revoke-all operation) should do that.
    token_sid = payload.get("sid")
    if token_sid:
        active_session = await AuthService.get_active_session_by_sid(
            db, user.id, token_sid
        )
        if active_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or revoked. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    if user.tenant and user.role != Role.SUPER_ADMIN.value:
        if not user.tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="تم إيقاف حساب العيادة مؤقتاً. يرجى التواصل مع الدعم الفني.",
            )

        entitlements = EntitlementService.evaluate_tenant_entitlements(user.tenant)
        if (
            request.method.upper() not in SAFE_IMPERSONATION_METHODS
            and not entitlements.can_write_clinical
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="انتهت صلاحية الاشتراك. يرجى التجديد للتمكن من الإضافة أو التعديل.",
            )

    from backend.core.tenancy import set_current_tenant_id, set_super_admin_bypass

    if user.role == Role.SUPER_ADMIN.value:
        set_super_admin_bypass(True)
    elif user.tenant_id:
        set_current_tenant_id(user.tenant_id)
        set_super_admin_bypass(False)
    else:
        logger.error(
            "Authenticated user '%s' (role=%s) has no tenant_id but is not super_admin",
            user.username,
            user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حسابك غير مربوط بعيادة. يرجى التواصل مع الإدارة لربط حسابك.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
