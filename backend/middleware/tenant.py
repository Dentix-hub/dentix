"""
Tenant Middleware — Sets tenant context early in request lifecycle.

This middleware extracts the tenant context from a signed JWT in either
the Authorization header or the httpOnly access-token cookie.
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
        tenant_token = None
        admin_token = None

        try:
            # Extract Token if present
            auth_header = request.headers.get("Authorization", "")
            token = request.cookies.get("access_token")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.removeprefix("Bearer ").strip()
            if token:
                try:
                    payload = auth.jwt.decode(
                        token,
                        auth.SECRET_KEY,
                        algorithms=[auth.ALGORITHM],
                    )
                    tenant_id = payload.get("tenant_id")
                    if tenant_id:
                        tenant_token = set_current_tenant_id(int(tenant_id))
                    if payload.get("role") == "super_admin":
                        admin_token = set_super_admin_bypass(True)
                except auth.JWTError:
                    # Expired or invalid token — do NOT set tenant context.
                    # Auth dependency will reject with 401 later.
                    pass

            response = await call_next(request)
            return response
        finally:
            # CRITICAL: Always clear tenant context after request
            # to prevent context bleeding across async tasks
            clear_tenant_context(tenant_token, admin_token)
