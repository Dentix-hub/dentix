"""
Tests for backend.core.target_guard
"""

import os
import pytest
from backend.core.target_guard import (
    UnsafeTargetError,
    validate_database_target,
    validate_http_target,
    sanitize_target_url,
)


def test_sanitize_target_url_strips_password():
    raw_url = "postgresql://dentix_user:superSecretPassword123@localhost:5432/dentix_test"
    sanitized = sanitize_target_url(raw_url)
    assert "superSecretPassword123" not in sanitized
    assert "localhost:5432/dentix_test" in sanitized
    assert ":***@" in sanitized


def test_validate_database_target_accepts_local_test_dbs():
    valid_urls = [
        "postgresql://postgres:pass@localhost:5432/dentix_test",
        "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/ephemeral_db",
        "postgresql://postgres:pass@postgres:5432/ci_db",
        "postgresql://postgres:pass@db:5432/dentix_local",
    ]
    for url in valid_urls:
        sanitized = validate_database_target(url)
        assert sanitized is not None
        assert "pass" not in sanitized


def test_validate_database_target_rejects_hosted_domains():
    invalid_urls = [
        "postgresql://postgres:pass@db.dentixs.app:5432/dentix_test",
        "postgresql://postgres:pass@aws-0-eu-central-1.pooler.supabase.co:6543/postgres",
        "postgresql://postgres:pass@app.hf.space:5432/dentix_test",
        "postgresql://postgres:pass@prod.digitalocean.com:5432/dentix_test",
    ]
    for url in invalid_urls:
        with pytest.raises(UnsafeTargetError):
            validate_database_target(url)


def test_validate_database_target_rejects_non_test_db_names():
    invalid_name_urls = [
        "postgresql://postgres:pass@localhost:5432/dentix_production",
        "postgresql://postgres:pass@localhost:5432/dentix_main",
        "postgresql://postgres:pass@localhost:5432/production",
    ]
    for url in invalid_name_urls:
        with pytest.raises(UnsafeTargetError):
            validate_database_target(url)


def test_validate_database_target_destructive_guard(monkeypatch):
    url = "postgresql://postgres:pass@localhost:5432/dentix_test"
    monkeypatch.delenv("LOCAL_DESTRUCTIVE_TESTS", raising=False)
    with pytest.raises(UnsafeTargetError, match="LOCAL_DESTRUCTIVE_TESTS=1"):
        validate_database_target(url, is_destructive=True)

    monkeypatch.setenv("LOCAL_DESTRUCTIVE_TESTS", "1")
    sanitized = validate_database_target(url, is_destructive=True)
    assert sanitized is not None


def test_validate_http_target_accepts_localhost():
    valid_http = [
        "http://localhost:8000/api/v1/health",
        "http://127.0.0.1:8000/api/v1/health",
    ]
    for url in valid_http:
        assert validate_http_target(url) == url


def test_validate_http_target_rejects_external_hosts():
    invalid_http = [
        "https://dentixs.app/api/v1/health",
        "https://staging.dentixs.app/api/v1/health",
        "https://hf.space/health",
        "https://vercel.app/api",
    ]
    for url in invalid_http:
        with pytest.raises(UnsafeTargetError):
            validate_http_target(url)
