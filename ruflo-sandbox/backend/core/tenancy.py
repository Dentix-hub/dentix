from contextvars import ContextVar
from typing import Optional

# Global context variable to store the current request's tenant_id
_tenant_id_ctx_var: ContextVar[Optional[int]] = ContextVar("tenant_id", default=None)


def get_current_tenant_id() -> Optional[int]:
    return _tenant_id_ctx_var.get()


def set_current_tenant_id(tenant_id: Optional[int]):
    _tenant_id_ctx_var.set(tenant_id)


def reset_current_tenant_id():
    _tenant_id_ctx_var.set(None)
