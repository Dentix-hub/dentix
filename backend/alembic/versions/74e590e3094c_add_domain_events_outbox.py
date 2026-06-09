"""Add domain events outbox

Revision ID: 74e590e3094c
Revises: e21aaee286c0
Create Date: 2026-05-13 00:26:46.088517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '74e590e3094c'
down_revision: Union[str, Sequence[str], None] = 'e21aaee286c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — ONLY adds the domain_events outbox table."""
    op.create_table('domain_events',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=255), nullable=False),
        sa.Column('aggregate_type', sa.String(length=255), nullable=False),
        sa.Column('aggregate_id', sa.String(length=255), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('available_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_domain_events_pending', 'domain_events', ['status', 'available_at'], unique=False)
    op.create_index(op.f('ix_domain_events_id'), 'domain_events', ['id'], unique=False)
    op.create_index(op.f('ix_domain_events_tenant_id'), 'domain_events', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema — drops the domain_events outbox table."""
    op.drop_index(op.f('ix_domain_events_tenant_id'), table_name='domain_events')
    op.drop_index(op.f('ix_domain_events_id'), table_name='domain_events')
    op.drop_index('idx_domain_events_pending', table_name='domain_events')
    op.drop_table('domain_events')
