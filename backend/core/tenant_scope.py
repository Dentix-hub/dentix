import contextvars
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria
from backend.database import Base

# Context variables for request-level storage
current_tenant_id = contextvars.ContextVar("current_tenant_id", default=None)
super_admin_bypass = contextvars.ContextVar("super_admin_bypass", default=False)

def set_current_tenant(tenant_id: int):
    """Set the current tenant ID for the context of this request."""
    return current_tenant_id.set(tenant_id)

def set_super_admin_bypass(bypass: bool = True):
    """Enable or disable bypass for the tenant scope filter (e.g. for super admin tasks)."""
    return super_admin_bypass.set(bypass)

def clear_tenant_context(tenant_token=None, admin_token=None):
    """Clear tenant context to prevent bleeding across async tasks."""
    if tenant_token:
        current_tenant_id.reset(tenant_token)
    if admin_token:
        super_admin_bypass.reset(admin_token)


@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    """
    Automatically appends a `.filter(Model.tenant_id == current_tenant)`
    clause to all ORM queries if the context is set and the model has a tenant_id.
    """
    # Only inject criteria for SELECT, UPDATE, DELETE requests
    if execute_state.is_select or execute_state.is_update or execute_state.is_delete:

        # 1. Super Admin checking all tenants
        if super_admin_bypass.get():
            return

        # 2. Extract tenant ID from context
        tenant_id = current_tenant_id.get()
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
