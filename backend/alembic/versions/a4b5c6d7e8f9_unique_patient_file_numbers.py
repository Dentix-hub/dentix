"""make patient file numbers unique inside each tenant

Revision ID: a4b5c6d7e8f9
Revises: 9f3a1c2d4e5f
Create Date: 2026-08-13 00:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "9f3a1c2d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT tenant_id, file_number, COUNT(*) AS duplicate_count
            FROM patients
            WHERE tenant_id IS NOT NULL AND file_number IS NOT NULL
            GROUP BY tenant_id, file_number
            HAVING COUNT(*) > 1
            LIMIT 10
            """
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError(
            "Cannot enforce unique patient file numbers; resolve duplicates first: "
            f"{duplicates}"
        )

    op.create_unique_constraint(
        "uq_patients_tenant_file_number",
        "patients",
        ["tenant_id", "file_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_patients_tenant_file_number", "patients", type_="unique"
    )
