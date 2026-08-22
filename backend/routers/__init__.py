# Backend Routers Package

# Keep the public router names stable while routing the three confirmed
# PostgreSQL NUMERIC regression surfaces through narrow compatibility facades.
# The underlying legacy modules remain importable for tests and rollback.
from . import accounting_decimal as accounting
from . import laboratories_decimal as laboratories
from . import metrics_decimal as metrics

__all__ = ["accounting", "laboratories", "metrics"]
