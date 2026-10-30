"""Optional email contracts and reversible SQLite migration."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from backend import models

PASSWORD = "Valid#Pass89!XyZ"


def register(client, headers, username, **extra):
    return client.post("/api/v1/users/register", json={
        "username": username, "password": PASSWORD, **extra,
    }, headers=headers)


def test_multiple_no_email_users_register_and_login(client, admin_headers, db_session):
    for username, extra in (("أحمد ", {}), ("فاطمة", {"email": "  "})):
        response = register(client, admin_headers, username, **extra)
        assert response.status_code == 200, response.text
        user = response.json()["data"]
        assert user["email"] is None
        stored = db_session.get(models.User, user["id"])
        assert stored.email is None
        assert stored.failed_login_attempts == 0
        assert stored.account_locked_until is None
        login = client.post("/api/v1/auth/token", data={
            "username": username, "password": PASSWORD,
        })
        assert login.status_code == 200, login.text
        assert login.json()["user"]["email"] is None


def test_email_creation_duplicates_and_clear_on_update(client, admin_headers):
    first = register(client, admin_headers, "with_email", email="  doctor@example.com  ")
    assert first.status_code == 200, first.text
    assert first.json()["data"]["email"] == "doctor@example.com"
    duplicate = register(client, admin_headers, "duplicate_email", email="doctor@example.com")
    assert duplicate.status_code == 400
    second = register(client, admin_headers, "second_email", email="second@example.com")
    assert second.status_code == 200
    duplicate_update = client.put(f"/api/v1/users/{second.json()['data']['id']}",
        json={"email": "doctor@example.com"}, headers=admin_headers)
    assert duplicate_update.status_code == 400
    clear = client.put(f"/api/v1/users/{first.json()['data']['id']}",
        json={"email": ""}, headers=admin_headers)
    assert clear.status_code == 200, clear.text
    assert clear.json()["data"]["email"] is None


def test_no_email_totp_and_profile_clear(client, admin_headers):
    clear = client.put("/api/v1/users/me", json={"email": "  "}, headers=admin_headers)
    assert clear.status_code == 200
    assert clear.json()["data"]["email"] is None
    setup = client.post("/api/v1/auth/2fa/setup", headers=admin_headers)
    assert setup.status_code == 200, setup.text
    assert "admin" in setup.json()["otp_uri"]
    assert setup.json()["secret"]


def test_password_reset_skips_no_email_users(client, admin_headers, monkeypatch):
    from backend.routers import password_reset
    assert register(client, admin_headers, "no_reset_email").status_code == 200
    send = Mock(side_effect=AssertionError("No delivery for an absent address"))
    monkeypatch.setattr(password_reset, "send_password_reset_email", send)
    response = client.post("/api/v1/auth/forgot-password", json={"email": "absent@example.com"})
    assert response.status_code == 200, response.text
    assert response.json()["message"] == "إذا كان البريد الإلكتروني موجوداً لدى النظام، ستصل رسالة لإعادة تعيين كلمة المرور"
    send.assert_not_called()


def test_user_model_normalizes_empty_email():
    user = models.User(username="example", email="  ")
    assert user.email is None
    user.email = " user@example.com "
    assert user.email == "user@example.com"
    user.email = ""
    assert user.email is None


def test_super_admin_can_clear_email(client, super_admin_headers):
    response = client.put("/api/v1/admin/system/profile",
        json={"email": "  "}, headers=super_admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["email"] is None


def test_optional_email_migration_sqlite_upgrade_downgrade():
    path = Path(__file__).parents[1] / "alembic/versions/1e2f3a4b5c6d_make_user_email_optional.py"
    spec = importlib.util.spec_from_file_location("optional_email_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL)"))
        connection.execute(sa.text("CREATE UNIQUE INDEX ix_users_email ON users(email)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            connection.execute(sa.text("INSERT INTO users (id,email) VALUES (1,NULL),(2,NULL),(3,'unique@example.com')"))
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(sa.text("INSERT INTO users (id,email) VALUES (4,'unique@example.com')"))
            with pytest.raises(RuntimeError, match="NULL emails exist"):
                migration.downgrade()
            assert sa.inspect(connection).get_columns("users")[1]["nullable"] is True
            connection.execute(sa.text("DELETE FROM users WHERE email IS NULL"))
            migration.downgrade()
            assert sa.inspect(connection).get_columns("users")[1]["nullable"] is False
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(sa.text("INSERT INTO users (id,email) VALUES (5,NULL)"))
            assert any(i["unique"] for i in sa.inspect(connection).get_indexes("users"))
            migration.upgrade()
    engine.dispose()
