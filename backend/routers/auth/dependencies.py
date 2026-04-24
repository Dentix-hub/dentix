import logging
logger = logging.getLogger(__name__)
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend import schemas, crud, auth
from backend.database import get_db
from backend.core.permissions import Role
from datetime import datetime, timezone

# OAuth Scheme (for Swagger UI / OpenAPI docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Bearer scheme with auto_error=False to allow cookie fallback
bearer_scheme = HTTPBearer(auto_error=False)


def get_token_from_header_or_cookie(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    access_token: str | None = Cookie(None),
) -> str | None:
    """Extract JWT from Authorization header or httpOnly cookie."""
    if credentials:
        return credentials.credentials
    return access_token


import string
import zxcvbn

def validate_password(password: str) -> None:
    """
    Validate password strength using complex rules and zxcvbn scoring.
    Raises HTTPException if validation fails.
    """
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تتكون من 8 أحرف على الأقل")

    # For Unicode scripts like Arabic, isupper/islower might not apply.
    # We check for general categories: letters, numbers, special chars.
    import re

    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    # Special characters: anything that is not alphanumeric and not a whitespace
    has_special = any(not c.isalnum() and not c.isspace() for c in password)

    if not (has_letter and has_digit and has_special):
        raise HTTPException(
            status_code=400,
            detail="كلمة المرور يجب أن تحتوي على حروف، أرقام، ورمز خاص واحد على الأقل"
        )

    # Optional: If English letters ARE present, we can still encourage case mix
    has_en_upper = any('A' <= c <= 'Z' for c in password)
    has_en_lower = any('a' <= c <= 'z' for c in password)
    has_en_letters = any(('A' <= c <= 'Z') or ('a' <= c <= 'z') for c in password)

    if has_en_letters and not (has_en_upper and has_en_lower):
        # We don't block, but if you're using English, you should mix cases.
        # However, to be safe and compatible with Arabic users, we won't raise error here
        # unless we strictly want to enforce it for English-only passwords.
        pass

    # ZXCVBN Score: 0 (weakest) to 4 (strongest)
    result = zxcvbn.zxcvbn(password)
    score = result.get('score', 0)
    if score < 3:
        feedback = result.get('feedback', {}).get('warning', "")
        details = f"كلمة المرور ضعيفة: {feedback}" if feedback else "كلمة المرور ضعيفة جداً ويمكن تخمينها بسهولة"
        raise HTTPException(
            status_code=400,
            detail=details
        )


def get_current_user(
    token: str | None = Depends(get_token_from_header_or_cookie), db: Session = Depends(get_db)
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
        # logger.info(f"DEBUG: Decoding token: {token[:10]}...")
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        # logger.info(f"DEBUG: Payload decoded: {payload}")
        username: str = payload.get("sub")
        tenant_id: int = payload.get("tenant_id")
        if username is None:
            # logger.info("DEBUG: Username is None")
            raise credentials_exception
        token_data = schemas.TokenData(username=username, tenant_id=tenant_id)
    except auth.JWTError as e:
        logger.debug("JWT error for user: %s", username if 'username' in locals() else "unknown")
        raise credentials_exception
    except Exception as e:
        logger.error("Unexpected authentication error: %s", e, exc_info=True)
        raise credentials_exception

    # Validated User
    user = crud.get_user(db, username=token_data.username)
    if user is None:
        logger.debug("User not found in DB for authenticated username: %s", token_data.username)
        raise credentials_exception

    # SINGLE SESSION POLICY: Validate Session ID
    token_sid = payload.get("sid")
    # Use getattr to prevent crash if column hasn't migrated yet
    active_session_val = getattr(user, "active_session_id", None)

    if token_sid and active_session_val:
        if token_sid != active_session_val:
            # logger.info(f"DEBUG: Session Mismatch. Token: {token_sid}, DB: {active_session_val}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="تم تسجيل الدخول من جهاز آخر. يرجى إعادة تسجيل الدخول.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Check Tenant Subscription
    if user.tenant and user.role != Role.SUPER_ADMIN.value:
        if not user.tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is inactive",
            )

        if (
            user.tenant.subscription_end_date
            and user.tenant.subscription_end_date < datetime.now(timezone.utc)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Subscription expired"
            )

    # SECURE: Inject tenant explicitly into Request Context for automatic SQLAlchemy scoping
    from backend.core.tenant_scope import set_current_tenant, set_super_admin_bypass

    if user.role == Role.SUPER_ADMIN.value:
        set_super_admin_bypass(True)
    elif user.tenant_id:
        set_current_tenant(user.tenant_id)
        set_super_admin_bypass(False)

    return user
