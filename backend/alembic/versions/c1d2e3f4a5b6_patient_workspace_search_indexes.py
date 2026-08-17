"""add patient workspace search indexes and age metadata

Revision ID: c1d2e3f4a5b6
Revises: f7a8b9c0d1e2
Create Date: 2026-08-17 16:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.core.security import get_encryption_manager
from backend.utils.patient_search_normalization import (
    normalize_patient_name_for_search,
    patient_phone_search_hash,
)

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("name_search_normalized", sa.String(), nullable=True))
    op.add_column("patients", sa.Column("phone_search_hash", sa.String(length=64), nullable=True))
    op.add_column("patients", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("patients", sa.Column("date_of_birth_precision", sa.String(length=32), nullable=True))
    op.add_column("patients", sa.Column("age_recorded_at", sa.DateTime(), nullable=True))

    op.create_index(
        "ix_patients_tenant_name_search",
        "patients",
        ["tenant_id", "name_search_normalized"],
        unique=False,
    )
    op.create_index(
        "ix_patients_tenant_phone_search",
        "patients",
        ["tenant_id", "phone_search_hash"],
        unique=False,
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, name, phone, age, created_at FROM patients")
    ).mappings().all()
    if not rows:
        return

    encryption = get_encryption_manager()
    updates = []
    for row in rows:
        phone_hash = None
        encrypted_phone = row["phone"]
        if encrypted_phone:
            plaintext_phone = encryption.decrypt(
                encrypted_phone, allow_plaintext_fallback=True
            )
            phone_hash = patient_phone_search_hash(plaintext_phone)
        updates.append(
            {
                "patient_id": row["id"],
                "name_search_normalized": normalize_patient_name_for_search(row["name"]),
                "phone_search_hash": phone_hash,
                "age_recorded_at": row["created_at"] if row["age"] and row["age"] > 0 else None,
            }
        )

    bind.execute(
        sa.text(
            """
            UPDATE patients
            SET name_search_normalized = :name_search_normalized,
                phone_search_hash = :phone_search_hash,
                age_recorded_at = :age_recorded_at
            WHERE id = :patient_id
            """
        ),
        updates,
    )


def downgrade() -> None:
    op.drop_index("ix_patients_tenant_phone_search", table_name="patients")
    op.drop_index("ix_patients_tenant_name_search", table_name="patients")
    op.drop_column("patients", "age_recorded_at")
    op.drop_column("patients", "date_of_birth_precision")
    op.drop_column("patients", "date_of_birth")
    op.drop_column("patients", "phone_search_hash")
    op.drop_column("patients", "name_search_normalized")
