import logging
logger = logging.getLogger(__name__)
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend import schemas, crud, auth
from backend.database import get_db
from backend.core.permissions import Role
from datetime import datetime, timezone

# OAuth Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


import string
import zxcvbn

def validate_password(password: str) -> None:
    """
    Validate password strength using complex rules and zxcvbn scoring.
    Raises HTTPException if validation fails.
    """
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تتكون من 8 أحرف على الأقل")

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in string.punctuation for c in password)

    if not (has_upper and has_lower and has_digit and has_special):
        raise HTTPException(
            status_code=400,
            detail="كلمة المرور يجب أن تحتوي على الأقل على حرف كبير، حرف صغير، رقم، ورمز خاص"
        )

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
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """Validate JWT token and return current user."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
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
        # logger.info(f"DEBUG: JWT Decode Error: {e}")
        # DEBUG: Add server time and token exp to error details
        try:
            # Decode without verification to get claims
            unsafe_payload = auth.jwt.decode(
                token,
                auth.SECRET_KEY,
                algorithms=[auth.ALGORITHM],
                options={"verify_signature": False, "verify_exp": False},
            )
            exp_claim = unsafe_payload.get("exp")
            server_time_utc = datetime.now(timezone.utc)
            server_time_ts = server_time_utc.timestamp()
            debug_info = f" | Server Time: {server_time_utc} ({server_time_ts}) | Token Exp: {exp_claim} | Diff: {float(exp_claim) - server_time_ts if exp_claim else 'N/A'}"
        except Exception:
            debug_info = " | Could not extract debug info"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT Error: {str(e)}{debug_info}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # logger.info(f"DEBUG: Unexpected Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth Error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validated User
    user = crud.get_user(db, username=token_data.username)
    if user is None:
        # logger.info(f"DEBUG: User not found in DB for username: {token_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User not found: {token_data.username}",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
            and user.tenant.subscription_end_date < datetime.utcnow()
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
