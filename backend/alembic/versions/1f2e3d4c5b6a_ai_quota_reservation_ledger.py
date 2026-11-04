"""ai quota reservation ledger

Revision ID: 1f2e3d4c5b6a
Revises: f5b6c7d8e9f0
Create Date: 2026-11-04

PR-07: Additive tenant-scoped usage and reservation ledger for atomic AI quota admission.
- ai_quota_windows: clinic-local daily quota window with UTC boundaries, timezone snapshot, and atomic counters
- ai_reservations: individual logical request reservations, fingerprint, scope, parent linkage, and lifecycle status
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "1f2e3d4c5b6a"
down_revision: Union[str, Sequence[str], None] = "f5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = (bind.dialect.name == "postgresql")
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Create ai_quota_windows
    if "ai_quota_windows" not in tables:
        tenant_fk = [sa.ForeignKey("tenants.id", ondelete="CASCADE")] if is_postgres else []
        op.create_table(
            "ai_quota_windows",
            sa.Column("id", sa.Integer(), primary_key=True, index=True, autoincrement=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                *tenant_fk,
                nullable=False,
                index=True,
            ),
            sa.Column("local_date", sa.Date(), nullable=False, index=True),
            sa.Column("start_utc", sa.DateTime(), nullable=False),
            sa.Column("end_utc", sa.DateTime(), nullable=False),
            sa.Column("timezone", sa.String(64), nullable=False),
            sa.Column("reserved_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("consumed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("uncertain_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_id", "local_date", name="uq_ai_quota_windows_tenant_local_date"),
            sa.CheckConstraint("start_utc < end_utc", name="ck_ai_quota_windows_bounds"),
            sa.CheckConstraint("reserved_count >= 0", name="ck_ai_quota_windows_reserved_nonneg"),
            sa.CheckConstraint("consumed_count >= 0", name="ck_ai_quota_windows_consumed_nonneg"),
            sa.CheckConstraint("uncertain_count >= 0", name="ck_ai_quota_windows_uncertain_nonneg"),
        )

    # 2. Create ai_reservations
    if "ai_reservations" not in tables:
        tenant_fk = [sa.ForeignKey("tenants.id", ondelete="CASCADE")] if is_postgres else []
        window_fk = [sa.ForeignKey("ai_quota_windows.id", ondelete="CASCADE")] if is_postgres else []
        user_fk = [sa.ForeignKey("users.id", ondelete="SET NULL")] if is_postgres else []
        op.create_table(
            "ai_reservations",
            sa.Column("id", sa.Integer(), primary_key=True, index=True, autoincrement=True),
            sa.Column("reservation_id", sa.String(36), nullable=False, unique=True, index=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                *tenant_fk,
                nullable=False,
                index=True,
            ),
            sa.Column(
                "window_id",
                sa.Integer(),
                *window_fk,
                nullable=False,
                index=True,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                *user_fk,
                nullable=True,
                index=True,
            ),
            sa.Column("operation", sa.String(64), nullable=False, index=True),
            sa.Column("request_fingerprint", sa.String(64), nullable=False),
            sa.Column("idempotency_key", sa.String(128), nullable=True, index=True),
            sa.Column("parent_reservation_id", sa.String(36), nullable=True, index=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="RESERVED", index=True),
            sa.Column("units", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("finalized_at", sa.DateTime(), nullable=True),
            sa.Column("error_reason", sa.String(255), nullable=True),
            sa.Column("reconciliation_notes", sa.Text(), nullable=True),
            sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_ai_reservations_tenant_idempotency"),
            sa.CheckConstraint("status IN ('RESERVED', 'CONSUMED', 'RELEASED', 'UNCERTAIN')", name="ck_ai_reservations_status"),
            sa.CheckConstraint("units >= 0", name="ck_ai_reservations_units_nonneg"),
        )

    # 3. Apply RLS on PostgreSQL
    if is_postgres:
        tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        bypass_expr = "CAST(NULLIF(current_setting('rls.bypass_rls', true), '') AS BOOLEAN) = true"

        # ai_quota_windows
        op.execute('ALTER TABLE "ai_quota_windows" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "ai_quota_windows" FORCE ROW LEVEL SECURITY')
        op.execute('DROP POLICY IF EXISTS "ai_quota_windows_tenant_policy" ON "ai_quota_windows"')
        op.execute(
            sa.text(
                f'''CREATE POLICY "ai_quota_windows_tenant_policy"
                    ON "ai_quota_windows"
                    FOR ALL
                    USING (({tenant_expr}) OR {bypass_expr})
                    WITH CHECK (({tenant_expr}) OR {bypass_expr})'''
            )
        )

        # ai_reservations
        op.execute('ALTER TABLE "ai_reservations" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "ai_reservations" FORCE ROW LEVEL SECURITY')
        op.execute('DROP POLICY IF EXISTS "ai_reservations_tenant_policy" ON "ai_reservations"')
        op.execute(
            sa.text(
                f'''CREATE POLICY "ai_reservations_tenant_policy"
                    ON "ai_reservations"
                    FOR ALL
                    USING (({tenant_expr}) OR {bypass_expr})
                    WITH CHECK (({tenant_expr}) OR {bypass_expr})'''
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = (bind.dialect.name == "postgresql")
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if is_postgres:
        if "ai_reservations" in tables:
            op.execute('DROP POLICY IF EXISTS "ai_reservations_tenant_policy" ON "ai_reservations"')
            op.execute('ALTER TABLE "ai_reservations" NO FORCE ROW LEVEL SECURITY')
            op.execute('ALTER TABLE "ai_reservations" DISABLE ROW LEVEL SECURITY')
        if "ai_quota_windows" in tables:
            op.execute('DROP POLICY IF EXISTS "ai_quota_windows_tenant_policy" ON "ai_quota_windows"')
            op.execute('ALTER TABLE "ai_quota_windows" NO FORCE ROW LEVEL SECURITY')
            op.execute('ALTER TABLE "ai_quota_windows" DISABLE ROW LEVEL SECURITY')

    if "ai_reservations" in tables:
        op.drop_table("ai_reservations")

    if "ai_quota_windows" in tables:
        op.drop_table("ai_quota_windows")
