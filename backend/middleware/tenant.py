"""
Tenant Middleware — Sets tenant context early in request lifecycle.

This middleware extracts the tenant_id from the JWT token in the
Authorization header and sets it in the unified tenant context.
The context is always cleaned up in the finally block.

Flow:
1. Reset tenant context at request start
2. Extract tenant_id from JWT (if present)
3. Set tenant context
4. Process request
5. Clean up tenant context in finally block
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from backend.core.tenancy import (
    set_current_tenant_id,
    reset_current_tenant_id,
    clear_tenant_context,
    set_super_admin_bypass,
)
from backend import auth
import logging

logger = logging.getLogger("smart_clinic.tenant_middleware")


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Always start with clean tenant context
        reset_current_tenant_id()
        set_super_admin_bypass(False)

        try:
            # Extract Token if present
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    payload = auth.jwt.decode(
                        token,
                        auth.SECRET_KEY,
                        algorithms=[auth.ALGORITHM],
                    )
                    tenant_id = payload.get("tenant_id")
                    if tenant_id:
                        set_current_tenant_id(tenant_id)
                except auth.JWTError:
                    # Expired or invalid token — do NOT set tenant context.
                    # Auth dependency will reject with 401 later.
                    pass

            response = await call_next(request)
            return response
        finally:
            # CRITICAL: Always clear tenant context after request
            # to prevent context bleeding across async tasks
            clear_tenant_context()
