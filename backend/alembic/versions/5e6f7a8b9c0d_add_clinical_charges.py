"""add clinical_charges ledger table

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-10-22

Phase G14 / Slice S32: Billing Policy Model & clinical_charges Ledger Table
- G14-M01: Define billing policy model (D1: completion creates a PENDING charge;
  reception creates the invoice)
- G14-M04: Design clinical_charges
- Applies R03 (composite tenant indexes + PostgreSQL parent-tenant / parent-patient
  triggers) and R05 (partial unique index: one active charge per work item)

Additive only: no existing table is altered. Legacy Treatment / Payment untouched.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5e6f7a8b9c0d"
down_revision: Union[str, Sequence[str], None] = "4d5e6f7a8b9c"
branch_labels = None
depends_on = None

TABLE = "clinical_charges"

# (child_key, parent_table, allow_null) -- mirrors preflight CHILD_TENANT_RELATIONSHIPS.
TENANT_RELATIONSHIPS = (
    ("patient_id", "patients", False),
    ("work_item_id", "clinical_work_items", False),
    ("care_session_id", "care_sessions", True),
    ("doctor_id", "users", True),
    ("legacy_treatment_id", "treatments", True),
)

# (child_key, parent_table, allow_null) -- mirrors preflight
# CLINICAL_CHARGES_DIRECT_PARENT_PATIENT_RELATIONSHIPS.
PATIENT_RELATIONSHIPS = (
    ("work_item_id", "clinical_work_items", False),
    ("care_session_id", "care_sessions", True),
)


def _tenant_trigger_name(child_key: str) -> str:
    return f"trg_{TABLE}_{child_key}_parent_tenant"


def _patient_trigger_name(child_key: str) -> str:
    return f"trg_{TABLE}_{child_key}_parent_patient"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if TABLE not in existing_tables:
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column(
                "work_item_id",
                sa.Integer(),
                sa.ForeignKey("clinical_work_items.id"),
                nullable=False,
            ),
            sa.Column(
                "care_session_id",
                sa.Integer(),
                sa.ForeignKey("care_sessions.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "doctor_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "legacy_treatment_id",
                sa.Integer(),
                sa.ForeignKey("treatments.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False),
            sa.Column(
                "discount", sa.Numeric(14, 2), nullable=False, server_default="0.00"
            ),
            sa.Column(
                "status", sa.String(length=32), nullable=False, server_default="pending"
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint("amount >= 0", name="ck_cc_amount_non_negative"),
            sa.CheckConstraint("discount >= 0", name="ck_cc_discount_non_negative"),
            sa.CheckConstraint("discount <= amount", name="ck_cc_discount_lte_amount"),
            sa.CheckConstraint(
                "status IN ('pending', 'invoiced', 'voided')", name="ck_cc_status"
            ),
        )

        for column in (
            "id",
            "tenant_id",
            "patient_id",
            "work_item_id",
            "care_session_id",
            "doctor_id",
            "legacy_treatment_id",
        ):
            op.create_index(f"ix_{TABLE}_{column}", TABLE, [column], unique=False)

        op.create_index("ix_cc_tenant_patient", TABLE, ["tenant_id", "patient_id"])
        op.create_index("ix_cc_tenant_status", TABLE, ["tenant_id", "status"])
        op.create_index("ix_cc_tenant_work_item", TABLE, ["tenant_id", "work_item_id"])
        op.create_index(
            "uq_cc_active_work_item",
            TABLE,
            ["tenant_id", "work_item_id"],
            unique=True,
            postgresql_where=sa.text("status != 'voided'"),
            sqlite_where=sa.text("status != 'voided'"),
        )

    if bind.dialect.name == "postgresql":
        tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{TABLE}" FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS "{TABLE}_tenant_policy" ON "{TABLE}"')
        op.execute(
            f'''CREATE POLICY "{TABLE}_tenant_policy" ON "{TABLE}"
                FOR ALL
                USING ({tenant_expr})
                WITH CHECK ({tenant_expr})'''
        )

        for child_key, parent, allow_null in TENANT_RELATIONSHIPS:
            trigger = _tenant_trigger_name(child_key)
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{TABLE}"')
            op.execute(
                f'''CREATE TRIGGER "{trigger}"
                    BEFORE INSERT OR UPDATE OF tenant_id, "{child_key}" ON "{TABLE}"
                    FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                        '{parent}', '{child_key}', '{str(allow_null).lower()}'
                    )'''
            )

        for child_key, parent, allow_null in PATIENT_RELATIONSHIPS:
            trigger = _patient_trigger_name(child_key)
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{TABLE}"')
            op.execute(
                f'''CREATE TRIGGER "{trigger}"
                    BEFORE INSERT OR UPDATE OF patient_id, "{child_key}" ON "{TABLE}"
                    FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_patient(
                        '{parent}', '{child_key}', '{str(allow_null).lower()}'
                    )'''
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if TABLE not in existing_tables:
        return

    if bind.dialect.name == "postgresql":
        for child_key, _, _ in PATIENT_RELATIONSHIPS:
            op.execute(f'DROP TRIGGER IF EXISTS "{_patient_trigger_name(child_key)}" ON "{TABLE}"')
        for child_key, _, _ in TENANT_RELATIONSHIPS:
            op.execute(f'DROP TRIGGER IF EXISTS "{_tenant_trigger_name(child_key)}" ON "{TABLE}"')
        op.execute(f'DROP POLICY IF EXISTS "{TABLE}_tenant_policy" ON "{TABLE}"')

    op.drop_table(TABLE)
