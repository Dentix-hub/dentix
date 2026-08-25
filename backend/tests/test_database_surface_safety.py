"""
Tests for P02-06: Regression test suite ensuring raw SQL database dump and restore endpoints remain permanently disabled.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.models import User, Tenant
from backend.core.permissions import Role
from backend.auth import create_access_token
from sqlalchemy.ext.asyncio import AsyncSession
import json


@pytest.mark.asyncio
async def test_raw_sql_download_returns_410_gone(async_db_session: AsyncSession):
    # Setup Super Admin user
    super_admin = User(
        username="super_admin_db_test",
        email="superadmin_db@dentix.test",
        hashed_password="hashed_secret",
        role=Role.SUPER_ADMIN.value,
        is_active=True,
    )
    async_db_session.add(super_admin)
    await async_db_session.commit()
    await async_db_session.refresh(super_admin)

    token = create_access_token(data={"sub": super_admin.username, "role": super_admin.role})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. /api/v1/settings/backup/download
        resp = await ac.get("/api/v1/settings/backup/download", headers=headers)
        assert resp.status_code == 410
        assert "disabled for security" in resp.json().get("detail", "").lower()

        # 2. /api/v1/admin/system/backup
        resp_sys = await ac.get("/api/v1/admin/system/backup", headers=headers)
        assert resp_sys.status_code == 410


@pytest.mark.asyncio
async def test_raw_sql_upload_and_restore_returns_410_gone(async_db_session: AsyncSession):
    super_admin = User(
        username="super_admin_upload_test",
        email="superadmin_upload@dentix.test",
        hashed_password="hashed_secret",
        role=Role.SUPER_ADMIN.value,
        is_active=True,
    )
    async_db_session.add(super_admin)
    await async_db_session.commit()
    await async_db_session.refresh(super_admin)

    token = create_access_token(data={"sub": super_admin.username, "role": super_admin.role})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. /api/v1/settings/backup/upload with .sql file
        files = {"file": ("backup.sql", b"DROP SCHEMA public CASCADE;", "application/sql")}
        resp = await ac.post("/api/v1/settings/backup/upload", files=files, headers=headers)
        assert resp.status_code == 410
        assert "permanently disabled" in resp.json().get("detail", "").lower()

        # 2. /api/v1/admin/system/restore
        resp_restore = await ac.post("/api/v1/admin/system/restore", files=files, headers=headers)
        assert resp_restore.status_code == 410


@pytest.mark.asyncio
async def test_tenant_scoped_json_export_and_restore_retained(async_db_session: AsyncSession):
    tenant = Tenant(name="Safe Export Clinic", is_active=True, subscription_status="active")
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    admin_user = User(
        username="clinic_admin_safe_export",
        email="admin@safeexport.test",
        hashed_password="hashed_secret",
        role=Role.ADMIN.value,
        tenant_id=tenant.id,
        is_active=True,
    )
    async_db_session.add(admin_user)
    await async_db_session.commit()
    await async_db_session.refresh(admin_user)

    token = create_access_token(
        data={"sub": admin_user.username, "tenant_id": tenant.id, "role": admin_user.role}
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Tenant JSON Export works
        resp_export = await ac.get("/api/v1/settings/backup/export", headers=headers)
        assert resp_export.status_code == 200
        data = resp_export.json()
        assert "data" in data
        assert "patients" in data["data"]

        # 2. Uploading a valid JSON backup payload works
        json_backup_bytes = json.dumps({
            "version": "1.0",
            "tenant_id": tenant.id,
            "backup_date": "2026-08-25T00:00:00Z",
            "data": {
                "patients": []
            }
        }).encode("utf-8")
        files = {"file": ("clinic_backup.json", json_backup_bytes, "application/json")}
        resp_upload = await ac.post("/api/v1/settings/backup/upload", files=files, headers=headers)
        assert resp_upload.status_code == 200
        assert resp_upload.json()["success"] is True
