import traceback
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.system import SystemError, ErrorLevel, ErrorSource

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
            
            # Log to Database (New Session)
            try:
                db: Session = SessionLocal()
                try:
                    system_error = SystemError(
                        level=ErrorLevel.ERROR,
                        source=ErrorSource.BACKEND,
                        message=error_msg,
                        stack_trace=stack_trace,
                        path=path,
                        method=method,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent")
                    )
                    db.add(system_error)
                    db.commit()
                except Exception as db_exc:
                    # Fallback to console if DB logging fails
                    print(f"CRITICAL: Failed to log error to DB: {db_exc}")
                finally:
                    db.close()
            except Exception as e:
                print(f"CRITICAL: Failed to create DB session for logging: {e}")
            
            # Re-raise so FastAPI's exception handler (or other middleware) can still catch it
            raise exc
