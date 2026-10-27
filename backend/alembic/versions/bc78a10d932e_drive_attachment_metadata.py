"""Add Drive attachment metadata without moving existing files.

Revision ID: bc78a10d932e
Revises: ab52d9c807a1
"""
from alembic import op
import sqlalchemy as sa

revision = 'bc78a10d932e'
down_revision = 'ab52d9c807a1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'attachments' not in existing_tables:
        return

    columns = {c['name'] for c in inspector.get_columns('attachments')}
    if 'storage_provider' not in columns:
        op.add_column('attachments', sa.Column('storage_provider', sa.String(32), nullable=False, server_default='legacy'))
    for name, length in [('storage_uuid', 36), ('drive_original_id', 255), ('drive_thumbnail_id', 255), ('original_sha256', 64), ('thumbnail_sha256', 64), ('google_account_sub', 255)]:
        if name not in columns:
            op.add_column('attachments', sa.Column(name, sa.String(length), nullable=True))
    if 'original_size' not in columns:
        op.add_column('attachments', sa.Column('original_size', sa.Integer(), nullable=True))
    if 'connection_generation' not in columns:
        op.add_column('attachments', sa.Column('connection_generation', sa.Integer(), nullable=True))
    if 'storage_status' not in columns:
        op.add_column('attachments', sa.Column('storage_status', sa.String(32), nullable=False, server_default='ready'))

    indexes = {idx['name'] for idx in inspector.get_indexes('attachments')}
    if 'uq_attachment_tenant_storage_uuid' not in indexes:
        op.create_index('uq_attachment_tenant_storage_uuid', 'attachments', ['tenant_id', 'storage_uuid'], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'attachments' not in existing_tables:
        return

    indexes = {idx['name'] for idx in inspector.get_indexes('attachments')}
    if 'uq_attachment_tenant_storage_uuid' in indexes:
        op.drop_index('uq_attachment_tenant_storage_uuid', table_name='attachments')

    columns = {c['name'] for c in inspector.get_columns('attachments')}
    for name in ('storage_status', 'connection_generation', 'original_size', 'google_account_sub', 'thumbnail_sha256', 'original_sha256', 'drive_thumbnail_id', 'drive_original_id', 'storage_uuid', 'storage_provider'):
        if name in columns:
            op.drop_column('attachments', name)
