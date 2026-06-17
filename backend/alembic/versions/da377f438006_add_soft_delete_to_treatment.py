"""add_soft_delete_to_treatment

Revision ID: da377f438006
Revises: bf6c75e1c3d3
Create Date: 2026-06-15 15:18:19.697595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da377f438006'
down_revision: Union[str, Sequence[str], None] = 'bf6c75e1c3d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('treatments', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('treatments', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('treatments', 'deleted_at')
    op.drop_column('treatments', 'is_deleted')
