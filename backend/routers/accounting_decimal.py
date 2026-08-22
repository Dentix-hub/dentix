"""Accounting router compatibility facade for PostgreSQL NUMERIC values."""

from importlib import import_module

from backend.services.accounting_decimal_service import DecimalSafeAccountingService

_base = import_module("backend.routers.accounting")


# Route callables in the layered accounting modules resolve ``AccountingService``
# from their module globals at request time. Point every layer at the safe
# compatibility facade so doctor revenue/details no longer mix Decimal and float.
_base.AccountingService = DecimalSafeAccountingService
_base._previous.AccountingService = DecimalSafeAccountingService
_base._previous._legacy.AccountingService = DecimalSafeAccountingService

router = _base.router

# Preserve the public module surface expected by imports/tests.
for _name in dir(_base):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_base, _name)
