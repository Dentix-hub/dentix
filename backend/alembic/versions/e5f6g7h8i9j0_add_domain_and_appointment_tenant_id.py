"""Add domain to tenants and tenant_id to appointments

Revision ID: e5f6g7h8i9j0
Revises: b0d1e2f3a4b5
Create Date: 2026-05-06 13:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, Sequence[str], None] = 'b0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # 1. Add domain to tenants
    tenant_columns = [c["name"] for c in inspector.get_columns("tenants")]
    if "domain" not in tenant_columns:
        op.add_column('tenants', sa.Column('domain', sa.String(), nullable=True))
        op.create_index(op.f('ix_tenants_domain'), 'tenants', ['domain'], unique=False)

    # 2. Add tenant_id to appointments
    appointment_columns = [c["name"] for c in inspector.get_columns("appointments")]
    if "tenant_id" not in appointment_columns:
        op.add_column('appointments', sa.Column('tenant_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_appointments_tenant_id', 'appointments', 'tenants', ['tenant_id'], ['id'])
        op.create_index(op.f('ix_appointments_tenant_id'), 'appointments', ['tenant_id'], unique=False)


def downgrade() -> None:
    # 1. Remove tenant_id from appointments
    op.drop_index(op.f('ix_appointments_tenant_id'), table_name='appointments')
    op.drop_constraint('fk_appointments_tenant_id', 'appointments', type_='foreignkey')
    op.drop_column('appointments', 'tenant_id')

    # 2. Remove domain from tenants
    op.drop_index(op.f('ix_tenants_domain'), table_name='tenants')
    op.drop_column('tenants', 'domain')
