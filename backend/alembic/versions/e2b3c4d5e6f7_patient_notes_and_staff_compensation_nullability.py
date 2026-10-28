"""Allow optional patient clinical notes/history and staff compensation fields.

Revision ID: e2b3c4d5e6f7
Revises: bc78a10d932e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'bc78a10d932e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'patients' in tables:
        patient_cols = {c['name']: c for c in inspector.get_columns('patients')}
        if bind.dialect.name == 'sqlite':
            with op.batch_alter_table('patients') as batch:
                if 'medical_history' in patient_cols and not patient_cols['medical_history']['nullable']:
                    batch.alter_column('medical_history', existing_type=sa.String(), nullable=True)
                if 'notes' in patient_cols and not patient_cols['notes']['nullable']:
                    batch.alter_column('notes', existing_type=sa.String(), nullable=True)
        else:
            if 'medical_history' in patient_cols and not patient_cols['medical_history']['nullable']:
                op.alter_column('patients', 'medical_history', existing_type=sa.String(), nullable=True)
            if 'notes' in patient_cols and not patient_cols['notes']['nullable']:
                op.alter_column('patients', 'notes', existing_type=sa.String(), nullable=True)

    if 'users' in tables:
        user_cols = {c['name']: c for c in inspector.get_columns('users')}
        if bind.dialect.name == 'sqlite':
            with op.batch_alter_table('users') as batch:
                if 'commission_percent' in user_cols and not user_cols['commission_percent']['nullable']:
                    batch.alter_column('commission_percent', existing_type=sa.Numeric(7, 4), nullable=True)
                if 'fixed_salary' in user_cols and not user_cols['fixed_salary']['nullable']:
                    batch.alter_column('fixed_salary', existing_type=sa.Numeric(14, 2), nullable=True)
                if 'per_appointment_fee' in user_cols and not user_cols['per_appointment_fee']['nullable']:
                    batch.alter_column('per_appointment_fee', existing_type=sa.Numeric(14, 2), nullable=True)
        else:
            if 'commission_percent' in user_cols and not user_cols['commission_percent']['nullable']:
                op.alter_column('users', 'commission_percent', existing_type=sa.Numeric(7, 4), nullable=True)
            if 'fixed_salary' in user_cols and not user_cols['fixed_salary']['nullable']:
                op.alter_column('users', 'fixed_salary', existing_type=sa.Numeric(14, 2), nullable=True)
            if 'per_appointment_fee' in user_cols and not user_cols['per_appointment_fee']['nullable']:
                op.alter_column('users', 'per_appointment_fee', existing_type=sa.Numeric(14, 2), nullable=True)


def downgrade() -> None:
    pass
