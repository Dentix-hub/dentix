"""Accounting compatibility facade for PostgreSQL NUMERIC values.

Keep the Decimal adapter scoped to the legacy accounting router module instead
of mutating the shared legacy service class.  The route objects (and therefore
their existing dependencies / RBAC guards) stay untouched, while endpoints
implemented by ``accounting_legacy`` instantiate the Decimal-safe final service.
"""

from importlib import import_module

from backend.services.accounting_decimal_service import DecimalSafeAccountingService


# The doctor-details route is originally defined in accounting_legacy and its
# endpoint resolves ``AccountingService`` from that module at call time.  Swap
# only that module-local reference.  Do NOT monkey-patch methods on the shared
# LegacyAccountingService class: doing so leaks into direct service tests and
# other consumers during the full backend suite.
_accounting_legacy_router = import_module("backend.routers.accounting_legacy")
_accounting_legacy_router.AccountingService = DecimalSafeAccountingService

_base = import_module("backend.routers.accounting")
router = _base.router

# Preserve the public module surface expected by imports/tests.
for _name in dir(_base):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_base, _name)
