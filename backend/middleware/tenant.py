"""
Tenant Middleware — Sets tenant context early in request lifecycle.

This middleware extracts the tenant_id from the JWT in the Authorization
header OR the httpOnly access_token cookie (the web app's default session
carrier) and sets it in the unified tenant context. Both carry the same
signed JWT, so the trust basis is identical: tenant binding happens only
after signature verification, before any database query runs.

HIGH-RLS-01: cookie-only sessions previously left the context empty, so a
NOBYPASSRLS application role could not resolve the very user row being
authenticated. Binding here restores FORCE RLS as the active isolation layer.

Flow:
1. Reset tenant context at request start
2. Extract tenant_id from signed JWT (header preferred, cookie fallback)
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

_ACCESS_TOKEN_COOKIE = "access_token"


def _tenant_id_from_signed_token(token: str) -> int | None:
    """Return tenant_id from a signature-verified JWT; None otherwise."""
    try:
        payload = auth.jwt.decode(
            token,
            auth.SECRET_KEY,
            algorithms=[auth.ALGORITHM],
        )
        tenant_id = payload.get("tenant_id")
        return int(tenant_id) if tenant_id else None
    except (auth.JWTError, TypeError, ValueError):
        # Expired or invalid token — do NOT set tenant context.
        # Auth dependency will reject with 401 later.
        return None


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Always start with clean tenant context
        reset_current_tenant_id()
        set_super_admin_bypass(False)

        try:
            # Prefer the Authorization header, then fall back to the signed
            # httpOnly cookie used by the web client.
            auth_header = request.headers.get("Authorization")
            tenant_id = None
            if auth_header and auth_header.startswith("Bearer "):
                tenant_id = _tenant_id_from_signed_token(auth_header.split(" ")[1])
            if tenant_id is None:
                cookie_token = request.cookies.get(_ACCESS_TOKEN_COOKIE)
                if cookie_token:
                    tenant_id = _tenant_id_from_signed_token(cookie_token)

            if tenant_id is not None:
                set_current_tenant_id(tenant_id)

            response = await call_next(request)
            return response
        finally:
            # CRITICAL: Always clear tenant context after request
            # to prevent context bleeding across async tasks
            clear_tenant_context()
