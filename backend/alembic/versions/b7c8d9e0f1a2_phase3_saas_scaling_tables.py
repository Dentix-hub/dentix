"""Add Phase 3 SaaS scaling tables and fields

Revision ID: b7c8d9e0f1a2
Revises: 6ce58b4d24ba, 74e590e3094c, e0eb7ca469b9, e146e0d57b66
Create Date: 2026-05-13 01:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = (
    "6ce58b4d24ba",
    "74e590e3094c",
    "e0eb7ca469b9",
    "e146e0d57b66",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    tables = _tables()

    if "feature_flags" not in tables:
        op.create_table(
            "feature_flags",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(), nullable=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("is_global_enabled", sa.Boolean(), nullable=True, server_default=sa.text("0")),
            sa.Column("rollout_percentage", sa.Integer(), nullable=True, server_default="0"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key"),
        )
        op.create_index(op.f("ix_feature_flags_id"), "feature_flags", ["id"], unique=False)
        op.create_index(op.f("ix_feature_flags_key"), "feature_flags", ["key"], unique=True)

    if "tenant_features" not in tables:
        op.create_table(
            "tenant_features",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("feature_key", sa.String(), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=True),
            sa.ForeignKeyConstraint(["feature_key"], ["feature_flags.key"]),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "feature_key", name="uq_tenant_features_tenant_key"),
        )
        op.create_index(op.f("ix_tenant_features_id"), "tenant_features", ["id"], unique=False)
        op.create_index(op.f("ix_tenant_features_tenant_id"), "tenant_features", ["tenant_id"], unique=False)
        op.create_index(op.f("ix_tenant_features_feature_key"), "tenant_features", ["feature_key"], unique=False)


    if "subscription_payments" in tables:
        _add_column_if_missing("subscription_payments", sa.Column("provider", sa.String(), nullable=True))
        _add_column_if_missing("subscription_payments", sa.Column("provider_payment_id", sa.String(), nullable=True))
        _add_column_if_missing("subscription_payments", sa.Column("provider_status", sa.String(), nullable=True))
        indexes = {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes("subscription_payments")}
        if "ix_subscription_payments_provider_payment_id" not in indexes:
            op.create_index(
                op.f("ix_subscription_payments_provider_payment_id"),
                "subscription_payments",
                ["provider_payment_id"],
                unique=False,
            )

    tables = _tables()


def downgrade() -> None:
    tables = _tables()
    if "tenant_features" in tables:
        op.drop_index(op.f("ix_tenant_features_feature_key"), table_name="tenant_features")
        op.drop_index(op.f("ix_tenant_features_tenant_id"), table_name="tenant_features")
        op.drop_index(op.f("ix_tenant_features_id"), table_name="tenant_features")
        op.drop_table("tenant_features")
    if "feature_flags" in tables:
        op.drop_index(op.f("ix_feature_flags_key"), table_name="feature_flags")
        op.drop_index(op.f("ix_feature_flags_id"), table_name="feature_flags")
        op.drop_table("feature_flags")
