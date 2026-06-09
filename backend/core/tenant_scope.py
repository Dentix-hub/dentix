"""
ORM-level tenant scope filter — automatically scopes all queries by tenant_id.

This module registers a SQLAlchemy event listener that injects tenant_id
filtering into every ORM query. It reads the tenant context from the
UNIFIED tenancy module (core/tenancy.py).

IMPORTANT: Do NOT create ContextVars in this module. All tenant state
is managed by core/tenancy.py.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria
from backend.database import Base
from backend.core.tenancy import (
    get_current_tenant_id,
    is_super_admin_bypass,
    set_current_tenant_id,
    set_super_admin_bypass,
    clear_tenant_context,
)

# Re-export for backward compatibility (modules that imported from here)
set_current_tenant = set_current_tenant_id


@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    """
    Automatically appends a `.filter(Model.tenant_id == current_tenant)`
    clause to all ORM queries if the context is set and the model has a tenant_id.
    """
    # Only inject criteria for SELECT, UPDATE, DELETE requests
    if execute_state.is_select or execute_state.is_update or execute_state.is_delete:

        # 1. Super Admin checking all tenants
        if is_super_admin_bypass():
            return

        # 2. Extract tenant ID from unified context
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            return  # Allow execution (might be auth login or initial system setup)

        # 3. Apply tenant criteria automatically to entities that actually have a tenant_id column
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            # Safely check if the mapped class actually has a 'tenant_id' column
            if "tenant_id" in mapper.columns:
                execute_state.statement = execute_state.statement.options(
                    with_loader_criteria(
                        cls,
                        # Using default arg 'c=cls' to avoid Python late-binding loop bugs
                        lambda c, bound_c=cls: bound_c.tenant_id == tenant_id,
                        include_aliases=True
                    )
                )
