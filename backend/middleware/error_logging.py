import logging
import traceback
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.database import AsyncSessionLocal, RlsContext
from backend.models.system import SystemError, ErrorLevel, ErrorSource

logger = logging.getLogger(__name__)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            # Capture the full stack trace
            error_msg = str(exc)
            stack_trace = traceback.format_exc()
            path = str(request.url)
            method = request.method

            # Log to Database (New Async Session)
            try:
                context = RlsContext(tenant_id=None)
                async with AsyncSessionLocal(context=context) as db:
                    async with db.bypass_rls() as db:  # system-level, no tenant
                        system_error = SystemError(
                            level=ErrorLevel.ERROR,
                            source=ErrorSource.BACKEND,
                            message=error_msg,
                            stack_trace=stack_trace,
                            path=path,
                            method=method,
                            ip_address=request.client.host if request.client else None,
                            user_agent=request.headers.get("user-agent"),
                        )
                        db.add(system_error)
                        await db.commit()
            except Exception as e:
                logger.critical("Failed to log error to DB: %s", e)

            # Re-raise so FastAPI's exception handler (or other middleware) can still catch it
            raise exc

