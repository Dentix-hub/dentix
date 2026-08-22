"""Accounting compatibility facade for PostgreSQL NUMERIC values.

Only the doctor-details service method is patched.  Avoid replacing
AccountingService module globals across the entire accounting router graph;
that broad monkey-patch changed unrelated endpoint and test behavior.
"""

from importlib import import_module

from backend.services.accounting_decimal_service import DecimalSafeAccountingService
from backend.services.accounting_service import AccountingService as BaseAccountingService


# Preserve every existing router dependency/permission and business route.  The
# target method keeps the same public contract while using Decimal-safe math.
BaseAccountingService.get_doctor_details_data = (
    DecimalSafeAccountingService.get_doctor_details_data
)

_base = import_module("backend.routers.accounting")
router = _base.router

# Preserve the public module surface expected by imports/tests.
for _name in dir(_base):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_base, _name)
