"""
Unified Tenant Context Module — Single source of truth for tenant isolation.

This module provides the ONLY mechanism for setting, getting, and clearing
the current request's tenant context. All other modules MUST import from here.

Architecture:
- Middleware sets tenant context early (from JWT in header)
- Auth dependency validates and confirms tenant context
- ORM filter reads tenant context to auto-scope queries
- Context is cleared in middleware's finally block

IMPORTANT: Never create additional ContextVars for tenant state elsewhere.
"""

from contextvars import ContextVar
from typing import Optional
import logging

logger = logging.getLogger("smart_clinic.tenancy")

# === SINGLE ContextVars for tenant state ===
_tenant_id_ctx_var: ContextVar[Optional[int]] = ContextVar("tenant_id", default=None)
_super_admin_bypass_ctx_var: ContextVar[bool] = ContextVar("super_admin_bypass", default=False)


# --- Getters ---
def get_current_tenant_id() -> Optional[int]:
    """Get the current request's tenant_id from context."""
    return _tenant_id_ctx_var.get()


def is_super_admin_bypass() -> bool:
    """Check if super admin bypass is active (cross-tenant access)."""
    return _super_admin_bypass_ctx_var.get()


# --- Setters ---
def set_current_tenant_id(tenant_id: Optional[int]):
    """Set the current request's tenant_id in context."""
    return _tenant_id_ctx_var.set(tenant_id)


def set_super_admin_bypass(bypass: bool = True):
    """Enable or disable tenant scope bypass for super admin operations."""
    return _super_admin_bypass_ctx_var.set(bypass)


# --- Cleanup ---
def reset_current_tenant_id():
    """Reset tenant_id to None (used at request start)."""
    _tenant_id_ctx_var.set(None)


def clear_tenant_context(tenant_token=None, admin_token=None):
    """Clear all tenant context to prevent bleeding across async tasks.
    
    Args:
        tenant_token: Token from set_current_tenant_id() to reset
        admin_token: Token from set_super_admin_bypass() to reset
    """
    if tenant_token:
        _tenant_id_ctx_var.reset(tenant_token)
    else:
        _tenant_id_ctx_var.set(None)
    
    if admin_token:
        _super_admin_bypass_ctx_var.reset(admin_token)
    else:
        _super_admin_bypass_ctx_var.set(False)
