"""secure subscription checkout and webhook processing

Revision ID: 9f3a1c2d4e5f
Revises: 0c0c38745bc3
Create Date: 2026-08-13 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f3a1c2d4e5f"
down_revision: Union[str, Sequence[str], None] = "0c0c38745bc3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT provider, provider_payment_id, COUNT(*) AS duplicate_count
            FROM subscription_payments
            WHERE provider IS NOT NULL AND provider_payment_id IS NOT NULL
            GROUP BY provider, provider_payment_id
            HAVING COUNT(*) > 1
            LIMIT 10
            """
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError(
            "Cannot enforce payment idempotency; resolve duplicate provider "
            f"payment IDs first: {duplicates}"
        )

    op.create_table(
        "subscription_checkouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_reference", sa.String(length=120), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("expected_amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="EGP"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=160), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_checkouts_provider_reference", "subscription_checkouts", ["provider_reference"], unique=True)
    op.create_index("ix_subscription_checkouts_tenant_id", "subscription_checkouts", ["tenant_id"])
    op.create_index("ix_subscription_checkouts_plan_id", "subscription_checkouts", ["plan_id"])
    op.create_index("ix_subscription_checkouts_provider", "subscription_checkouts", ["provider"])
    op.create_index("ix_subscription_checkouts_status", "subscription_checkouts", ["status"])
    op.create_unique_constraint(
        "uq_subscription_payment_provider_id",
        "subscription_payments",
        ["provider", "provider_payment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_subscription_payment_provider_id", "subscription_payments", type_="unique"
    )
    op.drop_index("ix_subscription_checkouts_status", table_name="subscription_checkouts")
    op.drop_index("ix_subscription_checkouts_provider", table_name="subscription_checkouts")
    op.drop_index("ix_subscription_checkouts_plan_id", table_name="subscription_checkouts")
    op.drop_index("ix_subscription_checkouts_tenant_id", table_name="subscription_checkouts")
    op.drop_index("ix_subscription_checkouts_provider_reference", table_name="subscription_checkouts")
    op.drop_table("subscription_checkouts")
