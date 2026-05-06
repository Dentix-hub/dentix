"""add contact_phone to tenants

Revision ID: d15e940112dd
Revises: e5f6g7h8i9j0
Create Date: 2026-05-06 17:46:12.201273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd15e940112dd'
down_revision: Union[str, Sequence[str], None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use inspector to check for column existence (safety for SQLite manual updates)
    from sqlalchemy.engine.reflection import Inspector
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    tenant_columns = [c["name"] for c in inspector.get_columns("tenants")]
    if "contact_phone" not in tenant_columns:
        op.add_column("tenants", sa.Column("contact_phone", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tenants", "contact_phone")
