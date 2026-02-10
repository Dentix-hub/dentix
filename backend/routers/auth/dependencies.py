from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend import schemas, crud, auth
from backend.database import get_db
from backend.constants import ROLES
from datetime import datetime, timezone

# OAuth Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def validate_password(password: str) -> bool:
    """
    Validate password strength.
    Requirements: min 6 chars, at least one letter AND one number.
    """
    if len(password) < 6:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    return has_letter and has_number


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
        # print(f"DEBUG: Decoding token: {token[:10]}...")
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        # print(f"DEBUG: Payload decoded: {payload}")
        username: str = payload.get("sub")
        tenant_id: int = payload.get("tenant_id")
        if username is None:
            # print("DEBUG: Username is None")
            raise credentials_exception
        token_data = schemas.TokenData(username=username, tenant_id=tenant_id)
    except auth.JWTError as e:
        # print(f"DEBUG: JWT Decode Error: {e}")
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
        # print(f"DEBUG: Unexpected Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth Error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validated User
    user = crud.get_user(db, username=token_data.username)
    if user is None:
        # print(f"DEBUG: User not found in DB for username: {token_data.username}")
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
            # print(f"DEBUG: Session Mismatch. Token: {token_sid}, DB: {active_session_val}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="تم تسجيل الدخول من جهاز آخر. يرجى إعادة تسجيل الدخول.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Check Tenant Subscription
    if user.tenant and user.role != ROLES.SUPER_ADMIN:
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

    return user
