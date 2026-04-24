import os
from fastapi import APIRouter
from .dependencies import get_current_user, get_db, oauth2_scheme, validate_password
from . import login, register, security, settings

# Create Main Router
router = APIRouter(tags=["Authentication"])

# Include Sub-Routers
router.include_router(login.router)
router.include_router(register.router)
router.include_router(security.router)
router.include_router(settings.router)

# Debug endpoints only in non-production
if os.getenv("ENVIRONMENT", "development").lower() != "production":
    from . import debug
    router.include_router(debug.router)

# Export for external usage
__all__ = ["router", "get_current_user", "get_db", "oauth2_scheme", "validate_password"]
