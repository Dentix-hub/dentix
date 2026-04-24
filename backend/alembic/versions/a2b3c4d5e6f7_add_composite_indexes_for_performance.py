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
    # Use inspector to check for existence
    from sqlalchemy.engine.reflection import Inspector
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Helper to create index if not exists
    def create_idx_safe(idx_name, table_name, columns):
        existing_indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
        if idx_name not in existing_indexes:
            op.create_index(idx_name, table_name, columns, unique=False)

    # Patient composite indexes
    create_idx_safe("idx_patient_tenant_active", "patients", ["tenant_id", "is_active"])
    create_idx_safe("idx_patient_tenant_deleted", "patients", ["tenant_id", "is_deleted"])
    create_idx_safe("idx_patient_name_search", "patients", ["name", "tenant_id"])
    create_idx_safe("idx_patient_phone", "patients", ["phone", "tenant_id"])
    create_idx_safe("idx_patient_created", "patients", ["tenant_id", "created_at"])

    # Appointment composite index
    create_idx_safe("idx_appointment_tenant_status_date", "appointments", ["tenant_id", "status", "date_time"])

    # Payment composite indexes
    create_idx_safe("idx_payment_tenant_date", "payments", ["tenant_id", "date"])
    create_idx_safe("idx_payment_patient", "payments", ["patient_id", "date"])

    # User composite index
    create_idx_safe("idx_user_tenant_role", "users", ["tenant_id", "role", "is_active"])

    # Treatment composite indexes
    create_idx_safe("idx_treatment_patient", "treatments", ["patient_id", "created_at"])
    create_idx_safe("idx_treatment_appointment", "treatments", ["appointment_id"])



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
