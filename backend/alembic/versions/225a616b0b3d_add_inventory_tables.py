"""Add inventory tables

Revision ID: 225a616b0b3d
Revises: ceb1e9e1108c
Create Date: 2026-01-31 00:19:00.717076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '225a616b0b3d'
down_revision: Union[str, Sequence[str], None] = 'ceb1e9e1108c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Warehouse
    op.create_table(
        'warehouses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), server_default='MAIN', nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_warehouses_id'), 'warehouses', ['id'], unique=False)
    op.create_index(op.f('ix_warehouses_tenant_id'), 'warehouses', ['tenant_id'], unique=False)

    # Material
    op.create_table(
        'materials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('base_unit', sa.String(), nullable=False),
        sa.Column('alert_threshold', sa.Integer(), server_default='10', nullable=True),
        sa.Column('packaging_ratio', sa.Float(), server_default='1.0', nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_materials_id'), 'materials', ['id'], unique=False)
    op.create_index(op.f('ix_materials_name'), 'materials', ['name'], unique=False)
    op.create_index(op.f('ix_materials_tenant_id'), 'materials', ['tenant_id'], unique=False)

    # Batch
    op.create_table(
        'batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('material_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('batch_number', sa.String(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('supplier', sa.String(), nullable=True),
        sa.Column('cost_per_unit', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_batches_expiry_date'), 'batches', ['expiry_date'], unique=False)
    op.create_index(op.f('ix_batches_id'), 'batches', ['id'], unique=False)
    op.create_index(op.f('ix_batches_material_id'), 'batches', ['material_id'], unique=False)

    # StockItem
    op.create_table(
        'stock_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), server_default='0.0', nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_items_batch_id'), 'stock_items', ['batch_id'], unique=False)
    op.create_index(op.f('ix_stock_items_id'), 'stock_items', ['id'], unique=False)
    op.create_index(op.f('ix_stock_items_warehouse_id'), 'stock_items', ['warehouse_id'], unique=False)

    # MaterialSession
    op.create_table(
        'material_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_item_id', sa.Integer(), nullable=False),
        sa.Column('opened_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('status', sa.String(), server_default='ACTIVE', nullable=True),
        sa.Column('remaining_est', sa.Float(), server_default='1.0', nullable=True),
        sa.Column('doctor_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['stock_item_id'], ['stock_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_material_sessions_id'), 'material_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_material_sessions_stock_item_id'), 'material_sessions', ['stock_item_id'], unique=False)

    # StockMovement
    op.create_table(
        'stock_movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_item_id', sa.Integer(), nullable=False),
        sa.Column('change_amount', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('reference_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('performed_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['stock_item_id'], ['stock_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_movements_id'), 'stock_movements', ['id'], unique=False)
    op.create_index(op.f('ix_stock_movements_stock_item_id'), 'stock_movements', ['stock_item_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_stock_movements_stock_item_id'), table_name='stock_movements')
    op.drop_index(op.f('ix_stock_movements_id'), table_name='stock_movements')
    op.drop_table('stock_movements')
    op.drop_index(op.f('ix_material_sessions_stock_item_id'), table_name='material_sessions')
    op.drop_index(op.f('ix_material_sessions_id'), table_name='material_sessions')
    op.drop_table('material_sessions')
    op.drop_index(op.f('ix_stock_items_warehouse_id'), table_name='stock_items')
    op.drop_index(op.f('ix_stock_items_id'), table_name='stock_items')
    op.drop_index(op.f('ix_stock_items_batch_id'), table_name='stock_items')
    op.drop_table('stock_items')
    op.drop_index(op.f('ix_batches_material_id'), table_name='batches')
    op.drop_index(op.f('ix_batches_id'), table_name='batches')
    op.drop_index(op.f('ix_batches_expiry_date'), table_name='batches')
    op.drop_table('batches')
    op.drop_index(op.f('ix_materials_tenant_id'), table_name='materials')
    op.drop_index(op.f('ix_materials_name'), table_name='materials')
    op.drop_index(op.f('ix_materials_id'), table_name='materials')
    op.drop_table('materials')
    op.drop_index(op.f('ix_warehouses_tenant_id'), table_name='warehouses')
    op.drop_index(op.f('ix_warehouses_id'), table_name='warehouses')
    op.drop_table('warehouses')
