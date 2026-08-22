import os

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text

from backend import models
from backend.core import security
from backend.schemas.tenant import Tenant as TenantSchema
from backend.services.backup_service import (
    build_pg_dump_command,
    build_psql_command,
    create_secure_temp_file,
)


def test_postgres_tool_commands_keep_password_out_of_argv():
    database_url = (
        "postgresql+asyncpg://dentix:top-secret@db.example:5432/dentix"
        "?sslmode=require"
    )

    dump_command, dump_env = build_pg_dump_command(database_url, "/tmp/dump.sql")
    restore_command, restore_env = build_psql_command(database_url, "/tmp/dump.sql")

    assert "top-secret" not in " ".join(dump_command)
    assert "top-secret" not in " ".join(restore_command)
    assert dump_env["PGPASSWORD"] == "top-secret"
    assert restore_env["PGPASSWORD"] == "top-secret"
    assert dump_env["PGSSLMODE"] == "require"


def test_secure_backup_temp_file_is_unique_and_removable():
    first = create_secure_temp_file(prefix="dentix_test_", suffix=".sql")
    second = create_secure_temp_file(prefix="dentix_test_", suffix=".sql")
    try:
        assert first != second
        assert os.path.exists(first)
        assert os.path.exists(second)
    finally:
        os.remove(first)
        os.remove(second)


@pytest.mark.asyncio
async def test_tenant_refresh_token_is_encrypted_at_rest(
    async_db_session, monkeypatch
):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    security.get_encryption_manager.cache_clear()

    tenant = models.Tenant(
        name="Encrypted Token Clinic",
        plan="trial",
        google_refresh_token="google-refresh-secret",
    )
    async_db_session.add(tenant)
    await async_db_session.commit()
    tenant_id = tenant.id

    raw_token = await async_db_session.scalar(
        text("SELECT google_refresh_token FROM tenants WHERE id = :tenant_id"),
        {"tenant_id": tenant_id},
    )
    assert raw_token != "google-refresh-secret"
    assert "google-refresh-secret" not in raw_token

    async_db_session.expire_all()
    loaded = await async_db_session.get(models.Tenant, tenant_id)
    assert loaded.google_refresh_token == "google-refresh-secret"

    schema = TenantSchema.model_validate(loaded)
    assert "google_refresh_token" not in schema.model_dump()
    security.get_encryption_manager.cache_clear()


def test_public_error_log_ignores_spoofed_identity_and_proxy_ip(client):
    response = client.post(
        "/api/v1/system/logs",
        headers={"x-forwarded-for": "203.0.113.99", "user-agent": "test-agent"},
        json={
            "level": "ERROR",
            "source": "BACKEND",
            "message": "frontend failed",
            "tenant_id": 999999,
            "user_id": 999999,
        },
    )

    assert response.status_code == 200
    logged = response.json()["data"]
    assert logged["source"] == "FRONTEND"
    assert logged["tenant_id"] is None
    assert logged["user_id"] is None
    assert logged["ip_address"] != "203.0.113.99"
    assert logged["user_agent"] == "test-agent"


def test_public_error_log_rejects_oversized_payload(client):
    response = client.post(
        "/api/v1/system/logs",
        json={"level": "ERROR", "message": "x" * 4001},
    )
    assert response.status_code == 422
