import pytest
from fastapi import HTTPException

from backend.routers.auth.dependencies import _enforce_impersonation_scope


def test_read_only_impersonation_allows_safe_methods():
    payload = {"is_impersonating": True, "impersonation_scope": "read_only"}
    for method in ["GET", "HEAD", "OPTIONS"]:
        _enforce_impersonation_scope(payload, method)


def test_read_only_impersonation_blocks_mutations():
    payload = {"is_impersonating": True, "impersonation_scope": "read_only"}
    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        with pytest.raises(HTTPException) as exc:
            _enforce_impersonation_scope(payload, method)
        assert exc.value.status_code == 403


def test_full_access_impersonation_keeps_explicit_mutation_scope():
    payload = {"is_impersonating": True, "impersonation_scope": "full_access"}
    _enforce_impersonation_scope(payload, "POST")


def test_invalid_impersonation_scope_is_rejected():
    payload = {"is_impersonating": True, "impersonation_scope": "unexpected"}
    with pytest.raises(HTTPException) as exc:
        _enforce_impersonation_scope(payload, "GET")
    assert exc.value.status_code == 401


def test_normal_tokens_are_unchanged():
    _enforce_impersonation_scope({"sub": "doctor"}, "POST")
