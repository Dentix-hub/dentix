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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'google_oauth_attempts' not in existing_tables:
        return

    columns = {c['name'] for c in inspector.get_columns('google_oauth_attempts')}
    for name in ('pending_account_sub', 'pending_root_id', 'pending_backup_id', 'pending_image_id'):
        if name not in columns:
            op.add_column('google_oauth_attempts', sa.Column(name, sa.String(255), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'google_oauth_attempts' not in existing_tables:
        return

    columns = {c['name'] for c in inspector.get_columns('google_oauth_attempts')}
    for name in ('pending_image_id', 'pending_backup_id', 'pending_root_id', 'pending_account_sub'):
        if name in columns:
            op.drop_column('google_oauth_attempts', name)
