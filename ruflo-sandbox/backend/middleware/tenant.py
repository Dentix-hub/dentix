from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from backend.core.tenancy import set_current_tenant_id, reset_current_tenant_id
from backend import auth
import logging

logger = logging.getLogger("smart_clinic")


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        reset_current_tenant_id()

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
