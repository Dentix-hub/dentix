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
    op.add_column('tenant_data_operations', sa.Column('request_key', sa.String(128), nullable=True))
    op.add_column('tenant_data_operations', sa.Column('remote_file_id', sa.String(255), nullable=True))
    op.add_column('tenant_data_operations', sa.Column('connection_generation', sa.Integer(), nullable=True))
    op.add_column('tenant_data_operations', sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tenant_data_operations', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('uq_tenant_data_operation_request', 'tenant_data_operations', ['tenant_id', 'kind', 'request_key'], unique=True)


def downgrade():
    op.drop_index('uq_tenant_data_operation_request', table_name='tenant_data_operations')
    for name in ('updated_at', 'attempts', 'connection_generation', 'remote_file_id', 'request_key'):
        op.drop_column('tenant_data_operations', name)
