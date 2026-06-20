"""fix_procedures_name_unique_scope

Revision ID: 0c0c38745bc3
Revises: da377f438006
Create Date: 2026-06-20 00:00:00.000000

Root-cause fix for ISSUE-06: `procedures.name` was declared
`Column(String, unique=True, index=True)`, making the name globally unique across
the entire table — including across tenants. But `Procedure.tenant_id` is
`nullable=True`, and the codebase uses a global-catalog + tenant-override pattern
(`or_(tenant_id == X, tenant_id.is_(None))` in crud/procedure.py and 7+ other
files). So two unrelated clinics could not both have a procedure named e.g.
"Scaling", which raised IntegrityError and (under client retry) cascaded into
QueuePool exhaustion.

The intended scope:
  - Tenant-scoped procedures (tenant_id IS NOT NULL): name unique WITHIN that tenant.
  - Global catalog procedures (tenant_id IS NULL): name unique AMONG globals.
  - The same name CAN be reused across two different tenants, and a tenant CAN
    reuse a name that also exists as a global default (override pattern).

PostgreSQL nuance: NULL != NULL for unique constraints/indexes, so a naive
UniqueConstraint('tenant_id','name') would NOT prevent two global rows from
sharing a name. Partial uniqueness can only be expressed as an INDEX in Postgres
(no WHERE clause on table-level CONSTRAINTs), hence two partial unique indexes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0c0c38745bc3'
down_revision: Union[str, Sequence[str], None] = 'da377f438006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Pre-flight data check. Abort (do NOT proceed) if either query finds rows.
    #    On the current data both lists should be empty: the old global
    #    unique=True index made duplicates impossible, so any non-empty result
    #    means something unexpected changed and a human must investigate.
    conn = op.get_bind()
    dupes_tenant = conn.execute(text(
        """
        SELECT tenant_id, name, COUNT(*) FROM procedures
        WHERE tenant_id IS NOT NULL
        GROUP BY tenant_id, name HAVING COUNT(*) > 1
        """
    )).fetchall()
    dupes_global = conn.execute(text(
        """
        SELECT name, COUNT(*) FROM procedures
        WHERE tenant_id IS NULL
        GROUP BY name HAVING COUNT(*) > 1
        """
    )).fetchall()
    if dupes_tenant or dupes_global:
        raise Exception(
            "Cannot apply migration: existing duplicate names found. "
            f"Tenant-scoped dupes: {dupes_tenant}. "
            f"Global dupes: {dupes_global}. "
            "Resolve manually before re-running this migration."
        )

    # 2. Drop the old global unique index (SQLAlchemy default name for
    #    `Column(... unique=True, index=True)` on a column named `name`).
    op.drop_index("ix_procedures_name", table_name="procedures")

    # 3. Create the two partial unique indexes. These mirror __table_args__ on
    #    Procedure in backend/models/clinical.py exactly.
    op.create_index(
        "uq_procedures_tenant_name", "procedures", ["tenant_id", "name"],
        unique=True, postgresql_where=text("tenant_id IS NOT NULL"),
    )
    op.create_index(
        "uq_procedures_global_name", "procedures", ["name"],
        unique=True, postgresql_where=text("tenant_id IS NULL"),
    )


# NOTE: downgrade is data-naive — if tenant-scoped duplicate names have
# accumulated since this migration went live, re-creating the global
# unique index below will fail. Resolve duplicates manually before downgrading.
def downgrade() -> None:
    # Reverse cleanly: restore the old global unique index and drop both partials.
    op.drop_index("uq_procedures_global_name", table_name="procedures")
    op.drop_index("uq_procedures_tenant_name", table_name="procedures")
    op.create_index("ix_procedures_name", "procedures", ["name"], unique=True)
