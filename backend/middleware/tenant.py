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
                # We decode without verifying expiration here just to get tenant_id
                # (Auth layer handles strict verification, this is just for context setting)
                # OR better: use same decode logic as auth.py but lightweight.
                # Ideally, dependencies happen AFTER middleware.
                # But we need tenant_id FOR the dependencies sometimes.
                # Let's trust auth.jwt.decode to be fast.
                payload = auth.jwt.decode(
                    token,
                    auth.SECRET_KEY,
                    algorithms=[auth.ALGORITHM],
                    options={"verify_exp": False},
                )
                tenant_id = payload.get("tenant_id")
                if tenant_id:
                    set_current_tenant_id(tenant_id)
                    # logger.info(f"Tenant Context Set: {tenant_id}")
            except Exception:
                # Invalid token, ignore (Auth dependency will catch it 401 later)
                pass

        response = await call_next(request)
        return response
