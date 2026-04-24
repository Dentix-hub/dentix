"""Add composite indexes for performance

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Patient composite indexes
    op.create_index(
        "idx_patient_tenant_active",
        "patients",
        ["tenant_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_patient_tenant_deleted",
        "patients",
        ["tenant_id", "is_deleted"],
        unique=False,
    )
    op.create_index(
        "idx_patient_name_search",
        "patients",
        ["name", "tenant_id"],
        unique=False,
    )
    op.create_index(
        "idx_patient_phone",
        "patients",
        ["phone", "tenant_id"],
        unique=False,
    )
    op.create_index(
        "idx_patient_created",
        "patients",
        ["tenant_id", "created_at"],
        unique=False,
    )

    # Appointment composite index
    op.create_index(
        "idx_appointment_tenant_status_date",
        "appointments",
        ["tenant_id", "status", "date_time"],
        unique=False,
    )

    # Payment composite indexes
    op.create_index(
        "idx_payment_tenant_date",
        "payments",
        ["tenant_id", "date"],
        unique=False,
    )
    op.create_index(
        "idx_payment_patient",
        "payments",
        ["patient_id", "date"],
        unique=False,
    )

    # User composite index
    op.create_index(
        "idx_user_tenant_role",
        "users",
        ["tenant_id", "role", "is_active"],
        unique=False,
    )

    # Treatment composite indexes
    op.create_index(
        "idx_treatment_patient",
        "treatments",
        ["patient_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_treatment_appointment",
        "treatments",
        ["appointment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_treatment_appointment", table_name="treatments")
    op.drop_index("idx_treatment_patient", table_name="treatments")
    op.drop_index("idx_user_tenant_role", table_name="users")
    op.drop_index("idx_payment_patient", table_name="payments")
    op.drop_index("idx_payment_tenant_date", table_name="payments")
    op.drop_index("idx_appointment_tenant_status_date", table_name="appointments")
    op.drop_index("idx_patient_created", table_name="patients")
    op.drop_index("idx_patient_phone", table_name="patients")
    op.drop_index("idx_patient_name_search", table_name="patients")
    op.drop_index("idx_patient_tenant_deleted", table_name="patients")
    op.drop_index("idx_patient_tenant_active", table_name="patients")
