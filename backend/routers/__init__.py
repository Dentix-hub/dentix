"""Backend routers package.

Finance Decimal hotfixes are exposed lazily so importing ``backend.routers`` does
not eagerly import the whole accounting/metrics/laboratory graph.  This keeps
the historical package import contract intact and avoids circular imports while
letting ``backend.main`` keep its stable ``from .routers import ...`` surface.
"""

from importlib import import_module

_DECIMAL_FACADES = {
    "accounting": "accounting_decimal",
    "laboratories": "laboratories_decimal",
    "metrics": "metrics_decimal",
}


def __getattr__(name: str):
    target = _DECIMAL_FACADES.get(name)
    if target is None:
        raise AttributeError(name)
    module = import_module(f"{__name__}.{target}")
    globals()[name] = module
    return module
