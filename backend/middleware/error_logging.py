import asyncio
import logging
import os
import traceback
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend import auth
from backend.database import AsyncSessionLocal, RlsContext, get_async_pool_status
from backend.models.system import SystemError, ErrorLevel, ErrorSource

logger = logging.getLogger(__name__)


def _get_error_log_timeout() -> float:
    try:
        return max(float(os.getenv("ERROR_LOG_DB_TIMEOUT_SECONDS", "2.0")), 0.1)
    except ValueError:
        logger.warning("Invalid ERROR_LOG_DB_TIMEOUT_SECONDS; using 2 seconds")
        return 2.0


ERROR_LOG_DB_TIMEOUT_SECONDS = _get_error_log_timeout()


def _coerce_optional_int(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_request_identity(request: Request) -> tuple[int | None, int | None]:
    """Resolve audit identifiers from trusted request state or a verified JWT."""
    current_user = getattr(request.state, "current_user", None)
    user_id = _coerce_optional_int(getattr(current_user, "id", None))
    tenant_id = _coerce_optional_int(getattr(current_user, "tenant_id", None))
    if tenant_id is not None:
        return user_id, tenant_id

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else None
    token = token or request.cookies.get("access_token")
    if not token:
        return user_id, None

    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except auth.JWTError:
        return user_id, None
    return user_id, _coerce_optional_int(payload.get("tenant_id"))


from backend.core.logging_sanitizer import sanitize_text, sanitize_stack_trace

async def _persist_system_error(
    *,
    request: Request,
    error_msg: str,
    stack_trace: str,
    user_id: int | None,
    tenant_id: int | None,
) -> None:
    context = RlsContext(tenant_id=None)
    sanitized_msg = sanitize_text(error_msg, max_length=4000) or "Unknown error"
    sanitized_trace = sanitize_stack_trace(stack_trace, max_length=12000)
    sanitized_path = sanitize_text(str(request.url), max_length=2048)

    async with AsyncSessionLocal(context=context) as db:
        async with db.bypass_rls() as db:  # system-level audit write
            db.add(
                SystemError(
                    level=ErrorLevel.ERROR,
                    source=ErrorSource.BACKEND,
                    message=sanitized_msg,
                    stack_trace=sanitized_trace,
                    path=sanitized_path,
                    method=request.method,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    ip_address=request.client.host if request.client else None,
                    user_agent=sanitize_text(request.headers.get("user-agent"), max_length=512),
                )
            )
            await db.commit()


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            error_msg = str(exc)
            stack_trace = traceback.format_exc()
            user_id, tenant_id = _get_request_identity(request)

            # stdout remains available even when the database pool is exhausted.
            logger.error(
                "Unhandled request error: %s %s: %s; pool=%s",
                request.method,
                request.url.path,
                error_msg,
                get_async_pool_status(),
                exc_info=(type(exc), exc, exc.__traceback__),
                extra={"user_id": user_id, "tenant_id": tenant_id},
            )

            try:
                await asyncio.wait_for(
                    _persist_system_error(
                        request=request,
                        error_msg=error_msg,
                        stack_trace=stack_trace,
                        user_id=user_id,
                        tenant_id=tenant_id,
                    ),
                    timeout=ERROR_LOG_DB_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.critical(
                    "Timed out after %.2fs while persisting system error; pool=%s",
                    ERROR_LOG_DB_TIMEOUT_SECONDS,
                    get_async_pool_status(),
                )
            except Exception as e:
                logger.critical(
                    "Failed to persist system error: %s; pool=%s",
                    e,
                    get_async_pool_status(),
                    exc_info=True,
                )

            raise
