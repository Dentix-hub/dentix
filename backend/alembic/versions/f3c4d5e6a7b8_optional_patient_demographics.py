"""Align optional patient demographics with the public API and historical data.

Revision ID: f3c4d5e6a7b8
Revises: e2b3c4d5e6f7
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3c4d5e6a7b8'
down_revision = 'e2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('patients'):
        return
    columns = {column['name']: column for column in inspector.get_columns('patients')}
    changes = [name for name in ('age', 'phone') if name in columns and not columns[name]['nullable']]
    if not changes:
        return
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('patients') as batch:
            for name in changes:
                batch.alter_column(name, existing_type=columns[name]['type'], nullable=True)
    else:
        for name in changes:
            op.alter_column('patients', name, existing_type=columns[name]['type'], nullable=True)


def downgrade():
    # Optional/unknown demographics must never be fabricated or discarded to
    # reintroduce NOT NULL. Retain the backward-compatible relaxed constraint.
    pass
