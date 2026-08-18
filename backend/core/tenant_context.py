"""Tenant-context helpers for authenticated clinic-scoped routes.

Platform-level accounts may legitimately have ``tenant_id=None``. Clinic-scoped
routers must reject that state explicitly instead of silently falling back to an
arbitrary tenant.
"""

from fastapi import HTTPException


def require_tenant_id(current_user) -> int:
    """Return the authenticated clinic tenant id or reject missing context.

    A missing tenant context is a request-boundary error. Falling back to a
    concrete tenant (historically tenant ``1`` in some routes) is unsafe because
    it can cross the tenant-isolation boundary.
    """

    tenant_id = getattr(current_user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=400,
            detail="Tenant context is required for this clinic-scoped operation.",
        )
    return int(tenant_id)
