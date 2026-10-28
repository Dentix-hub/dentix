import base64
from unittest.mock import patch
import pytest

from backend.auth import create_access_token


def _headers(user):
    return {
        "Authorization": "Bearer "
        + create_access_token(
            data={"sub": user.username, "tenant_id": user.tenant_id, "role": user.role}
        )
    }


def test_backup_status_reports_archive_configured_true_when_valid(
    client, admin_user, monkeypatch
):
    key_32_bytes = base64.urlsafe_b64encode(b"k" * 32).decode()
    monkeypatch.setenv("TENANT_BACKUP_KEY_ID", "key-2026")
    monkeypatch.setenv("TENANT_BACKUP_ENCRYPTION_KEY", key_32_bytes)
    monkeypatch.setenv("DENTIX_INSTALLATION_ID", "inst-1234")
    monkeypatch.setenv("TENANT_BACKUP_MAX_BYTES", "1000000")

    response = client.get("/api/v1/settings/backup/status", headers=_headers(admin_user))
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["archive_configured"] is True
    assert data["archive_unconfigured_reason"] is None


def test_backup_status_reports_archive_configured_false_when_missing(
    client, admin_user, monkeypatch
):
    monkeypatch.delenv("TENANT_BACKUP_KEY_ID", raising=False)
    monkeypatch.delenv("TENANT_BACKUP_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("DENTIX_INSTALLATION_ID", raising=False)

    response = client.get("/api/v1/settings/backup/status", headers=_headers(admin_user))
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["archive_configured"] is False
    assert data["archive_unconfigured_reason"] == "إعدادات النسخ الاحتياطي غير مكتملة"


def test_backup_status_reports_archive_configured_false_when_invalid_key(
    client, admin_user, monkeypatch
):
    monkeypatch.setenv("TENANT_BACKUP_KEY_ID", "key-2026")
    monkeypatch.setenv("TENANT_BACKUP_ENCRYPTION_KEY", "not-a-valid-base64-or-length")
    monkeypatch.setenv("DENTIX_INSTALLATION_ID", "inst-1234")

    response = client.get("/api/v1/settings/backup/status", headers=_headers(admin_user))
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["archive_configured"] is False
    assert data["archive_unconfigured_reason"] == "إعدادات مفاتيح النسخ الاحتياطي غير صالحة"


def test_backup_status_safe_fallback_on_unexpected_exception(
    client, admin_user, monkeypatch
):
    with patch(
        "backend.services.tenant_archive.configured_keys",
        side_effect=RuntimeError("/var/secret/path/failed.so: segmentation fault"),
    ):
        response = client.get("/api/v1/settings/backup/status", headers=_headers(admin_user))
        assert response.status_code == 200, response.text
        data = response.json()["data"]

        assert data["archive_configured"] is False
        assert data["archive_unconfigured_reason"] == "إعدادات النسخ الاحتياطي غير مكتملة"
        assert "/var/secret" not in data["archive_unconfigured_reason"]
