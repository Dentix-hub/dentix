"""add_rls_policies

Revision ID: bf6c75e1c3d3
Revises: b7c8d9e0f1a2
Create Date: 2026-06-14 12:05:34.145829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf6c75e1c3d3'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES_WITH_RLS = [
    "users",
    "patients",
    "saved_medications",
    "appointments",
    "treatments",
    "treatment_sessions",
    "laboratories",
    "lab_orders",
    "procedures",
    "payments",
    "expenses",
    "salary_payments",
    "lab_payments",
    "insurance_providers",
    "price_lists",
    "warehouses",
    "materials",
    "batches",
    "stock_items",
    "procedure_material_weights",
    "material_learning_logs",
    "treatment_material_usages",
    "audit_logs",
    "support_messages",
    "tenant_features",
    "background_jobs",
    "system_errors",
    "ai_logs",
    "security_events",
    "domain_events"
]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Loop through tables to enable RLS and create tenant policy
    for table in TABLES_WITH_RLS:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        
        expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        bypass = "CAST(NULLIF(current_setting('rls.bypass_rls', true), '') AS BOOLEAN) = true"
        
        op.execute(f"""
            CREATE POLICY {table}_tenant_policy ON {table}
            FOR ALL
            USING (({expr}) OR {bypass})
            WITH CHECK (({expr}) OR {bypass});
        """)

    # Special case: notifications
    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE notifications FORCE ROW LEVEL SECURITY;")
    notif_expr = "(tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer) OR (is_global = true) OR (tenant_id IS NULL)"
    bypass = "CAST(NULLIF(current_setting('rls.bypass_rls', true), '') AS BOOLEAN) = true"
    op.execute(f"""
        CREATE POLICY notifications_tenant_policy ON notifications
        FOR ALL
        USING (({notif_expr}) OR {bypass})
        WITH CHECK (({notif_expr}) OR {bypass});
    """)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in TABLES_WITH_RLS:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_policy ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS notifications_tenant_policy ON notifications;")
    op.execute("ALTER TABLE notifications DISABLE ROW LEVEL SECURITY;")
