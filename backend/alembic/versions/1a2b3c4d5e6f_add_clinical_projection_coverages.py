"""add clinical projection coverages

Revision ID: 1a2b3c4d5e6f
Revises: f4a5b6c7d8e9
Create Date: 2026-09-09

Adds tenant-owned Clinical Projection Coverage persistence table:
- clinical_projection_coverages

Enforces natural uniqueness for tenant+patient+domain, tenant ownership,
patient relationship, and PostgreSQL ENABLE/FORCE RLS following the repository's
current patterns.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None

COVERAGE_DOMAINS = ("teeth", "treatments", "sessions")
COVERAGE_DOMAIN_CLAUSE = ", ".join(f"'{d}'" for d in COVERAGE_DOMAINS)

COVERAGE_STATES = ("UNCOVERED", "PARTIAL", "COMPLETE")
COVERAGE_STATE_CLAUSE = ", ".join(f"'{s}'" for s in COVERAGE_STATES)


def upgrade() -> None:
    op.create_table(
        "clinical_projection_coverages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="UNCOVERED", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version_id", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            f"domain IN ({COVERAGE_DOMAIN_CLAUSE})",
            name="ck_cpc_domain",
        ),
        sa.CheckConstraint(
            f"status IN ({COVERAGE_STATE_CLAUSE})",
            name="ck_cpc_status",
        ),
        sa.UniqueConstraint("tenant_id", "patient_id", "domain", name="uq_cpc_tenant_patient_domain"),
    )

    op.create_index("ix_cpc_tenant_patient", "clinical_projection_coverages", ["tenant_id", "patient_id"])
    op.create_index("ix_cpc_tenant_domain", "clinical_projection_coverages", ["tenant_id", "domain"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        table = "clinical_projection_coverages"
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS "{table}_tenant_policy" ON "{table}"')
        op.execute(
            f'''CREATE POLICY "{table}_tenant_policy" ON "{table}"
                FOR ALL
                USING ({tenant_expr})
                WITH CHECK ({tenant_expr})'''
        )

        trigger_name = "trg_clinical_projection_coverages_patient_id_parent_tenant"
        op.execute(f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{table}"')
        op.execute(
            f'''CREATE TRIGGER "{trigger_name}"
                BEFORE INSERT OR UPDATE OF tenant_id, "patient_id" ON "{table}"
                FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                    'patients', 'patient_id', 'false'
                )'''
        )


def downgrade() -> None:
    bind = op.get_bind()
    table = "clinical_projection_coverages"
    if bind.dialect.name == "postgresql":
        trigger_name = "trg_clinical_projection_coverages_patient_id_parent_tenant"
        op.execute(f'DROP TRIGGER IF EXISTS "{trigger_name}" ON "{table}"')
        op.execute(f'DROP POLICY IF EXISTS "{table}_tenant_policy" ON "{table}"')

    op.drop_index("ix_cpc_tenant_domain", table_name=table)
    op.drop_index("ix_cpc_tenant_patient", table_name=table)
    op.drop_table(table)
