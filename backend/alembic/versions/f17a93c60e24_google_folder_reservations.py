"""Keep stable folder IDs across interrupted Google provisioning.

Revision ID: f17a93c60e24
Revises: e82c19f5a406
"""
from alembic import op
import sqlalchemy as sa

revision = 'f17a93c60e24'
down_revision = 'e82c19f5a406'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('pending_account_sub', 'pending_root_id', 'pending_backup_id', 'pending_image_id'):
        op.add_column('google_oauth_attempts', sa.Column(name, sa.String(255), nullable=True))


def downgrade():
    for name in ('pending_image_id', 'pending_backup_id', 'pending_root_id', 'pending_account_sub'):
        op.drop_column('google_oauth_attempts', name)
