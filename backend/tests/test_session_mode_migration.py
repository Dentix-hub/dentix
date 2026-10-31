"""Session-mode migration preserves legacy rows and accepts both modes."""
from alembic import command
from alembic.config import Config
import sqlalchemy as sa


def test_session_mode_upgrade_and_roundtrip(tmp_path, monkeypatch, legacy_clinical_schema):
    url = f"sqlite:///{tmp_path / 'sessions.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("backend/alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        legacy_clinical_schema(conn)
        conn.execute(sa.text("CREATE TABLE tenants (id INTEGER PRIMARY KEY, google_refresh_token VARCHAR)"))
        conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE attachments (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
        conn.execute(sa.text("CREATE TABLE treatments (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
        conn.execute(sa.text("CREATE TABLE clinical_work_items (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
        conn.execute(sa.text("CREATE TABLE user_sessions (id INTEGER PRIMARY KEY, user_id INTEGER, token_hash VARCHAR, ip_address VARCHAR, user_agent VARCHAR, device_info VARCHAR, last_active_at DATETIME, expires_at DATETIME, is_active BOOLEAN, created_at DATETIME)"))
        conn.execute(sa.text("INSERT INTO user_sessions (id, user_id, token_hash) VALUES (1, 1, 'old')"))
    command.stamp(config, "1e2f3a4b5c6d")
    command.upgrade(config, "head")
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO user_sessions (id, token_hash) VALUES (2, 'default')"))
        conn.execute(sa.text("INSERT INTO user_sessions (id, token_hash, remember_me) VALUES (3, 'session', false)"))
        assert conn.execute(sa.text("SELECT remember_me FROM user_sessions ORDER BY id")).scalars().all() == [1, 1, 0]
    command.downgrade(config, "1e2f3a4b5c6d")
    assert "remember_me" not in {c['name'] for c in sa.inspect(engine).get_columns('user_sessions')}
    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT remember_me FROM user_sessions ORDER BY id")).scalars().all() == [1, 1, 1]
    engine.dispose()
