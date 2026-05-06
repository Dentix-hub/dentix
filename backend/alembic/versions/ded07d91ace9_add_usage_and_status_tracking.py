"""add_usage_and_status_tracking

Revision ID: ded07d91ace9
Revises: d15e940112dd
Create Date: 2026-05-06 23:59:45.459077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ded07d91ace9'
down_revision: Union[str, Sequence[str], None] = 'd15e940112dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add status to treatments
    op.add_column('treatments', sa.Column('status', sa.String(), nullable=True, server_default='Done'))
    
    # Add max_uses to materials
    op.add_column('materials', sa.Column('max_uses', sa.Integer(), nullable=True, server_default='1'))
    
    # Add current_uses to material_sessions
    op.add_column('material_sessions', sa.Column('current_uses', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('material_sessions', 'current_uses')
    op.drop_column('materials', 'max_uses')
    op.drop_column('treatments', 'status')
