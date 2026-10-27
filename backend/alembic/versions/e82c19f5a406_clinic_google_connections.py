"""Add clinic Google connection state and tenant-isolated OAuth attempts.

Revision ID: e82c19f5a406
Revises: d42a71e9bc83
"""
from alembic import op
import sqlalchemy as sa

revision = 'e82c19f5a406'
down_revision = 'd42a71e9bc83'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tenants', sa.Column('google_account_sub', sa.String(255), nullable=True))
    op.add_column('tenants', sa.Column('google_account_email', sa.String(320), nullable=True))
    op.add_column('tenants', sa.Column('google_connection_status', sa.String(32), nullable=False, server_default='disconnected'))
    op.add_column('tenants', sa.Column('google_connection_generation', sa.Integer(), nullable=False, server_default='0'))
    op.execute("UPDATE tenants SET google_connection_status = 'needs_reconnect' WHERE google_refresh_token IS NOT NULL")
    for name in ('google_root_folder_id', 'google_backup_folder_id', 'google_image_folder_id'):
        op.add_column('tenants', sa.Column(name, sa.String(255), nullable=True))
    op.create_table('google_oauth_attempts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('state_digest', sa.String(64), nullable=False, unique=True),
        sa.Column('browser_digest', sa.String(64), nullable=False),
        sa.Column('nonce_digest', sa.String(64), nullable=False),
        sa.Column('verifier', sa.String(1024), nullable=False),
        sa.Column('connection_generation', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_google_oauth_attempts_tenant_id', 'google_oauth_attempts', ['tenant_id'])
    if op.get_bind().dialect.name == 'postgresql':
        tenant = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        op.execute('ALTER TABLE google_oauth_attempts ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE google_oauth_attempts FORCE ROW LEVEL SECURITY')
        op.execute(f'CREATE POLICY google_oauth_attempts_tenant_policy ON google_oauth_attempts FOR ALL USING ({tenant}) WITH CHECK ({tenant})')


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP POLICY IF EXISTS google_oauth_attempts_tenant_policy ON google_oauth_attempts')
    op.drop_index('ix_google_oauth_attempts_tenant_id', table_name='google_oauth_attempts')
    op.drop_table('google_oauth_attempts')
    for name in ('google_image_folder_id', 'google_backup_folder_id', 'google_root_folder_id', 'google_connection_generation', 'google_connection_status', 'google_account_email', 'google_account_sub'):
        op.drop_column('tenants', name)
