"""Old treatment and native work-item rows remain explicitly unknown."""
import importlib.util
from pathlib import Path
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_lab_choice_migration_preserves_unknown_rows():
    path = Path(__file__).parents[1] / 'alembic/versions/9ab047d5613e_lab_choice_columns.py'
    spec = importlib.util.spec_from_file_location('lab_choice_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(sa.text('CREATE TABLE treatments (id INTEGER PRIMARY KEY)'))
        connection.execute(sa.text('CREATE TABLE clinical_work_items (id INTEGER PRIMARY KEY)'))
        connection.execute(sa.text('INSERT INTO treatments (id) VALUES (1)'))
        connection.execute(sa.text('INSERT INTO clinical_work_items (id) VALUES (1)'))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert connection.execute(sa.text('SELECT lab_choice FROM treatments')).scalar_one() is None
            assert connection.execute(sa.text('SELECT lab_choice FROM clinical_work_items')).scalar_one() is None
            connection.execute(sa.text("UPDATE treatments SET lab_choice='in_clinic' WHERE id=1"))
            assert connection.execute(sa.text('SELECT lab_choice FROM treatments')).scalar_one() == 'in_clinic'
            migration.downgrade()
            assert 'lab_choice' not in {column['name'] for column in sa.inspect(connection).get_columns('treatments')}
            migration.upgrade()
            assert connection.execute(sa.text('SELECT lab_choice FROM treatments')).scalar_one() is None
    engine.dispose()
