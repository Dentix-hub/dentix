"""backfill finance event tenant ids

Revision ID: f2a4c6e8b0d1
Revises: c1d2e3f4a5b6
Create Date: 2026-08-19

Historical Dentix rows may have a NULL tenant_id on child/event tables even
though their owning Patient/Treatment/Laboratory/User is tenant-scoped.  FORCE
RLS correctly hides those NULL rows, so repair the stored tenant ownership
instead of weakening the policy.
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a4c6e8b0d1"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def _execute(sql: str) -> None:
    op.execute(sa.text(sql))


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Migrations are privileged maintenance work.  Temporarily opt into the
        # existing explicit RLS bypass so FORCE RLS does not hide the rows that
        # need repair.  Policies remain unchanged and strict after this tx.
        _execute("SET LOCAL rls.bypass_rls = 'true'")

    _execute(
        """
        UPDATE treatments AS child
        SET tenant_id = owner.tenant_id
        FROM patients AS owner
        WHERE child.patient_id = owner.id
          AND child.tenant_id IS NULL
          AND owner.tenant_id IS NOT NULL
        """
    )
    _execute(
        """
        UPDATE payments AS child
        SET tenant_id = owner.tenant_id
        FROM patients AS owner
        WHERE child.patient_id = owner.id
          AND child.tenant_id IS NULL
          AND owner.tenant_id IS NOT NULL
        """
    )
    _execute(
        """
        UPDATE appointments AS child
        SET tenant_id = owner.tenant_id
        FROM patients AS owner
        WHERE child.patient_id = owner.id
          AND child.tenant_id IS NULL
          AND owner.tenant_id IS NOT NULL
        """
    )
    _execute(
        """
        UPDATE lab_orders AS child
        SET tenant_id = owner.tenant_id
        FROM patients AS owner
        WHERE child.patient_id = owner.id
          AND child.tenant_id IS NULL
          AND owner.tenant_id IS NOT NULL
        """
    )
    _execute(
        """
        UPDATE treatment_sessions AS child
        SET tenant_id = owner.tenant_id
        FROM treatments AS owner
        WHERE child.treatment_id = owner.id
          AND child.tenant_id IS NULL
          AND owner.tenant_id IS NOT NULL
        """
    )
    _execute(
        """
        UPDATE lab_payments AS child
        SET tenant_id = owner.tenant_id
        FROM laboratories AS owner
        WHERE child.laboratory_id = owner.id
          AND child.tenant_id IS NULL
          AND owner.tenant_id IS NOT NULL
        """
    )
    _execute(
        """
        UPDATE salary_payments AS child
        SET tenant_id = owner.tenant_id
        FROM users AS owner
        WHERE child.user_id = owner.id
          AND child.tenant_id IS NULL
          AND owner.tenant_id IS NOT NULL
        """
    )

    if bind.dialect.name == "postgresql":
        _execute("SET LOCAL rls.bypass_rls = 'false'")


def downgrade() -> None:
    # This is a deterministic data repair.  Re-introducing NULL tenant IDs would
    # destroy valid ownership information and is therefore intentionally not
    # reversible.
    pass
