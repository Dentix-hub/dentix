"""Add durable idempotent metadata for tenant Drive backups.

Revision ID: ab52d9c807a1
Revises: f17a93c60e24
"""
from alembic import op
import sqlalchemy as sa

revision = 'ab52d9c807a1'
down_revision = 'f17a93c60e24'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'tenant_data_operations' not in existing_tables:
        return

    columns = {c['name'] for c in inspector.get_columns('tenant_data_operations')}
    if 'request_key' not in columns:
        op.add_column('tenant_data_operations', sa.Column('request_key', sa.String(128), nullable=True))
    if 'remote_file_id' not in columns:
        op.add_column('tenant_data_operations', sa.Column('remote_file_id', sa.String(255), nullable=True))
    if 'connection_generation' not in columns:
        op.add_column('tenant_data_operations', sa.Column('connection_generation', sa.Integer(), nullable=True))
    if 'attempts' not in columns:
        op.add_column('tenant_data_operations', sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'))
    if 'updated_at' not in columns:
        op.add_column('tenant_data_operations', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    indexes = {idx['name'] for idx in inspector.get_indexes('tenant_data_operations')}
    if 'uq_tenant_data_operation_request' not in indexes:
        op.create_index('uq_tenant_data_operation_request', 'tenant_data_operations', ['tenant_id', 'kind', 'request_key'], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'tenant_data_operations' not in existing_tables:
        return

    indexes = {idx['name'] for idx in inspector.get_indexes('tenant_data_operations')}
    if 'uq_tenant_data_operation_request' in indexes:
        op.drop_index('uq_tenant_data_operation_request', table_name='tenant_data_operations')

    columns = {c['name'] for c in inspector.get_columns('tenant_data_operations')}
    for name in ('updated_at', 'attempts', 'connection_generation', 'remote_file_id', 'request_key'):
        if name in columns:
            op.drop_column('tenant_data_operations', name)
