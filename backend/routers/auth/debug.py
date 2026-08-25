import logging
logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas, crud, auth
from .dependencies import get_async_db
from sqlalchemy import text, select, func
from backend.core.permissions import Permission, require_permission
import traceback
from backend.core.response import success_response, error_response

router = APIRouter()


# --- Debug Endpoints ---
@router.get("/debug-token")
async def debug_token_validation(token: str, db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    """Debug endpoint to validate a token manually and see the error."""
    try:
        logger.info("DEBUG: Validating token signature and claims")
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username = payload.get("sub")

        user = await crud.get_user(db, username=username)
        if not user:
            return error_response(message="User not found in DB", data={"valid": False})

        return success_response(data={
            "valid": True,
            "username": username,
            "role": user.role,
            "user_id": user.id,
            "tenant_id": user.tenant_id,
        })
    except Exception:
        logger.warning("Token validation failed")
        return error_response(message="Token validation failed", data={"valid": False})


@router.get("/debug-auth-info")
async def debug_auth_info(db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    """Debug endpoint to check DB and Schema status."""
    try:
        # Check connection
        await db.execute(text("SELECT 1"))

        # Check Tables
        # Simple cross-db compatible check
        try:
            # SQLite
            result = await db.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result]
        except Exception:
            # Postgres
            result = await db.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
            )
            tables = [row[0] for row in result]

        # Check Users
        user_count_stmt = select(func.count(models.User.id))
        result_user_count = await db.execute(user_count_stmt)
        user_count = result_user_count.scalar() or 0

        first_user_stmt = select(models.User).limit(1)
        result_first_user = await db.execute(first_user_stmt)
        first_user = result_first_user.scalars().first()

        # Check Columns in User
        user_cols = []
        if first_user:
            user_cols = list(first_user.__dict__.keys())

        return success_response(data={
            "status": "ok",
            "db_connected": True,
            "tables": tables,
            "user_count": user_count,
            "sample_user_has_2fa": hasattr(first_user, "is_2fa_enabled")
            if first_user
            else False,
            "user_cols_raw": str(user_cols),
        })
    except Exception as e:
        logger.error(f"DB inspection failed: {str(e)}", exc_info=True)
        return error_response(message="DB inspection failed", data={"status": "error"})


@router.get("/debug/ping")
def debug_ping():
    """Simple ping to verify router is active."""
    return success_response(data={"message": "pong", "router": "auth"})


@router.get("/debug/manual-db")
async def debug_manual_db(current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    """Manually create session to test DB connection without Depends()."""
    try:
        from backend.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            return success_response(data={"status": "ok", "message": "Manual DB Session Successful"})
    except Exception as e:
        logger.error(f"DB inspection failed: {str(e)}", exc_info=True)
        return error_response(message="DB inspection failed", data={"status": "error"})


from fastapi import HTTPException

@router.get("/debug/fix-schema")
@router.get("/auth/debug/fix-schema")
async def fix_staging_schema(
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Disabled for security. Database schema changes must be applied via Alembic migrations."""
    raise HTTPException(
        status_code=410,
        detail="Dynamic schema fix over HTTP has been permanently disabled. Use Alembic migrations.",
    )
