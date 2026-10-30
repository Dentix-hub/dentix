"""The compatibility migration changes constraints, never demographic values."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import sqlalchemy as sa


@pytest.mark.parametrize('already_nullable', [False, True])
def test_migration_preserves_rows_and_is_repeatable(already_nullable):
    path = Path(__file__).parents[1] / 'alembic/versions/f3c4d5e6a7b8_optional_patient_demographics.py'
    spec = importlib.util.spec_from_file_location('optional_demographics_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine('sqlite:///:memory:')
    metadata = sa.MetaData()
    patients = sa.Table(
        'patients', metadata, sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('age', sa.Integer, nullable=already_nullable),
        sa.Column('phone', sa.String, nullable=already_nullable),
        sa.Column('name', sa.String, nullable=False),
    )
    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(patients.insert().values(id=1, age=35, phone='synthetic', name='Synthetic'))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        migration.upgrade()
        columns = {column['name']: column for column in sa.inspect(connection).get_columns('patients')}
        assert columns['age']['nullable'] and columns['phone']['nullable']
        assert not columns['name']['nullable']
        assert connection.execute(sa.select(patients)).one() == (1, 35, 'synthetic', 'Synthetic')
        connection.execute(patients.insert().values(id=2, age=None, phone=None, name='Unknown'))
        migration.downgrade()
        assert connection.execute(sa.select(patients).where(patients.c.id == 2)).one() == (2, None, None, 'Unknown')
    engine.dispose()
