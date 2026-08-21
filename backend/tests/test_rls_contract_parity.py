from backend import models
from backend.scripts.preflight_migrations import RLS_TABLES


def _tenant_scoped_model_tables() -> set[str]:
    return {
        table.name
        for table in models.Base.metadata.tables.values()
        if "tenant_id" in table.c
    }


def test_every_tenant_scoped_model_table_is_in_production_rls_contract():
    model_tables = _tenant_scoped_model_tables()
    configured = set(RLS_TABLES) | {"notifications"}

    missing = sorted(model_tables - configured)
    stale = sorted(configured - model_tables)

    assert not missing and not stale, (
        "Production RLS contract drift detected. "
        f"missing={missing}, stale={stale}, "
        f"model_tables={sorted(model_tables)}, configured={sorted(configured)}"
    )


def test_tenant_rls_parity_is_complete_not_percentage_based():
    model_tables = _tenant_scoped_model_tables()
    configured = set(RLS_TABLES) | {"notifications"}

    assert model_tables == configured
