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
    inspector = sa.inspect(bind)
    column_names = {
        column["name"] for column in inspector.get_columns("patients")
    }

    # Older production databases predate ``file_number`` because their core
    # schema was created before this Alembic chain. Fresh databases already
    # get the column from the model baseline, so support both shapes.
    if "file_number" not in column_names:
        op.add_column(
            "patients",
            sa.Column("file_number", sa.Integer(), nullable=True),
        )

    # Continue numbering after the current tenant maximum. On legacy schemas
    # this assigns deterministic 1..N numbers per tenant without collisions.
    op.execute(
        sa.text(
            """
            WITH ranked_missing AS (
                SELECT
                    id,
                    tenant_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY tenant_id ORDER BY id
                    ) AS row_number
                FROM patients
                WHERE file_number IS NULL
            ),
            tenant_maximums AS (
                SELECT tenant_id, COALESCE(MAX(file_number), 0) AS maximum
                FROM patients
                GROUP BY tenant_id
            )
            UPDATE patients
            SET file_number = (
                SELECT tenant_maximums.maximum + ranked_missing.row_number
                FROM ranked_missing
                JOIN tenant_maximums
                  ON tenant_maximums.tenant_id = ranked_missing.tenant_id
                  OR (
                      tenant_maximums.tenant_id IS NULL
                      AND ranked_missing.tenant_id IS NULL
                  )
                WHERE ranked_missing.id = patients.id
            )
            WHERE file_number IS NULL
            """
        )
    )

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

    inspector = sa.inspect(bind)
    index_names = {
        index["name"] for index in inspector.get_indexes("patients")
    }
    if "ix_patients_file_number" not in index_names:
        op.create_index(
            "ix_patients_file_number",
            "patients",
            ["file_number"],
        )

    constraint_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("patients")
    }
    if "uq_patients_tenant_file_number" not in constraint_names:
        op.create_unique_constraint(
            "uq_patients_tenant_file_number",
            "patients",
            ["tenant_id", "file_number"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraint_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("patients")
    }
    if "uq_patients_tenant_file_number" in constraint_names:
        op.drop_constraint(
            "uq_patients_tenant_file_number", "patients", type_="unique"
        )

    index_names = {
        index["name"] for index in inspector.get_indexes("patients")
    }
    if "ix_patients_file_number" in index_names:
        op.drop_index("ix_patients_file_number", table_name="patients")
