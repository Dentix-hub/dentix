"""Accounting compatibility facade for PostgreSQL NUMERIC values.

Patch only the legacy doctor-details implementation where PostgreSQL NUMERIC
values first meet float-oriented compensation math.  Keeping the patch at the
legacy boundary preserves every Finance V2 wrapper layered above it (period,
legacy-row compatibility, hire-date proration) and leaves router dependencies
and permissions untouched.
"""

from importlib import import_module

from backend.services.accounting_decimal_service import DecimalSafeAccountingService
from backend.services.accounting_service_legacy import (
    AccountingService as LegacyAccountingService,
)


# The final AccountingService subclasses several Finance V2 correctness layers.
# Do not replace its top-level method: doing so bypasses those wrappers in the
# full test suite.  Replace only the legacy implementation that contains the
# Decimal/float boundary; normal calls still flow through every newer override.
LegacyAccountingService.get_doctor_details_data = (
    DecimalSafeAccountingService.get_doctor_details_data
)

_base = import_module("backend.routers.accounting")
router = _base.router

# Preserve the public module surface expected by imports/tests.
for _name in dir(_base):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_base, _name)
