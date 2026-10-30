"""Add tenant-isolated durable restore operation state.

Revision ID: c38f91a2d47b
Revises: ba7526e3a901
"""
from alembic import op
import sqlalchemy as sa

revision = 'c38f91a2d47b'
down_revision = 'ba7526e3a901'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'tenant_data_operations' not in existing_tables:
        op.create_table(
            'tenant_data_operations',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('kind', sa.String(32), nullable=False),
            sa.Column('status', sa.String(32), nullable=False),
            sa.Column('archive_digest', sa.String(64), nullable=False),
            sa.Column('confirmation_digest', sa.String(64), nullable=False),
            sa.Column('encrypted_payload', sa.Text(), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('error_code', sa.String(64), nullable=True),
        )
        op.create_index('ix_tenant_data_operations_tenant_id', 'tenant_data_operations', ['tenant_id'])
        op.create_index('ix_tenant_data_operations_tenant_status', 'tenant_data_operations', ['tenant_id', 'status'])
        if op.get_bind().dialect.name == 'postgresql':
            tenant = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
            op.execute('ALTER TABLE tenant_data_operations ENABLE ROW LEVEL SECURITY')
            op.execute('ALTER TABLE tenant_data_operations FORCE ROW LEVEL SECURITY')
            op.execute(f'CREATE POLICY tenant_data_operations_tenant_policy ON tenant_data_operations FOR ALL USING ({tenant}) WITH CHECK ({tenant})')


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if 'tenant_data_operations' in existing_tables:
        if op.get_bind().dialect.name == 'postgresql':
            op.execute('DROP POLICY IF EXISTS tenant_data_operations_tenant_policy ON tenant_data_operations')
        indexes = {idx['name'] for idx in inspector.get_indexes('tenant_data_operations')}
        if 'ix_tenant_data_operations_tenant_status' in indexes:
            op.drop_index('ix_tenant_data_operations_tenant_status', table_name='tenant_data_operations')
        if 'ix_tenant_data_operations_tenant_id' in indexes:
            op.drop_index('ix_tenant_data_operations_tenant_id', table_name='tenant_data_operations')
        op.drop_table('tenant_data_operations')
