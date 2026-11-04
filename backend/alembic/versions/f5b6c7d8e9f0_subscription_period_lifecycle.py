"""subscription period lifecycle and scheduled downgrade storage

Revision ID: f5b6c7d8e9f0
Revises: e4a5b6c7d8e9
Create Date: 2026-11-04

PR-06: Additive columns on tenants table for subscription periods, billing day anchors,
preserved trial remainder, future plan assignments, and scheduled downgrades.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "f5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "e4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = (bind.dialect.name == "postgresql")
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "tenants" in tables:
        tenant_cols = {c["name"] for c in inspector.get_columns("tenants")}
        has_sub_plans = ("subscription_plans" in tables)

        if is_postgres:
            if "billing_day_anchor" not in tenant_cols:
                op.add_column("tenants", sa.Column("billing_day_anchor", sa.Integer(), nullable=True))
            if "subscription_start_date" not in tenant_cols:
                op.add_column("tenants", sa.Column("subscription_start_date", sa.DateTime(), nullable=True))
            if "future_plan_id" not in tenant_cols:
                fk = sa.ForeignKey("subscription_plans.id", ondelete="SET NULL", name="fk_tenants_future_plan_id") if has_sub_plans else None
                op.add_column("tenants", sa.Column("future_plan_id", sa.Integer(), fk, nullable=True))
            if "future_plan_start_date" not in tenant_cols:
                op.add_column("tenants", sa.Column("future_plan_start_date", sa.DateTime(), nullable=True))
            if "scheduled_downgrade_plan_id" not in tenant_cols:
                fk = sa.ForeignKey("subscription_plans.id", ondelete="SET NULL", name="fk_tenants_scheduled_downgrade_plan_id") if has_sub_plans else None
                op.add_column("tenants", sa.Column("scheduled_downgrade_plan_id", sa.Integer(), fk, nullable=True))
        else:
            with op.batch_alter_table("tenants") as batch_op:
                if "billing_day_anchor" not in tenant_cols:
                    batch_op.add_column(sa.Column("billing_day_anchor", sa.Integer(), nullable=True))
                if "subscription_start_date" not in tenant_cols:
                    batch_op.add_column(sa.Column("subscription_start_date", sa.DateTime(), nullable=True))
                if "future_plan_id" not in tenant_cols:
                    batch_op.add_column(sa.Column("future_plan_id", sa.Integer(), nullable=True))
                if "future_plan_start_date" not in tenant_cols:
                    batch_op.add_column(sa.Column("future_plan_start_date", sa.DateTime(), nullable=True))
                if "scheduled_downgrade_plan_id" not in tenant_cols:
                    batch_op.add_column(sa.Column("scheduled_downgrade_plan_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = (bind.dialect.name == "postgresql")
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "tenants" in tables:
        tenant_cols = {c["name"] for c in inspector.get_columns("tenants")}
        cols_to_drop = [
            "scheduled_downgrade_plan_id",
            "future_plan_start_date",
            "future_plan_id",
            "subscription_start_date",
            "billing_day_anchor",
        ]
        if is_postgres:
            for col in cols_to_drop:
                if col in tenant_cols:
                    op.drop_column("tenants", col)
        else:
            with op.batch_alter_table("tenants") as batch_op:
                for col in cols_to_drop:
                    if col in tenant_cols:
                        batch_op.drop_column(col)
