from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.services import file_service


def test_get_file_path_allows_file_inside_upload_root(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    tenant_dir = upload_root / "tenant_1"
    tenant_dir.mkdir(parents=True)
    allowed = tenant_dir / "allowed.txt"
    allowed.write_text("ok", encoding="utf-8")

    monkeypatch.setattr(file_service, "_get_upload_root", lambda: upload_root)

    resolved = file_service.get_file_path("tenant_1/allowed.txt")
    assert resolved == allowed.resolve()


def test_get_file_path_blocks_parent_traversal(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(file_service, "_get_upload_root", lambda: upload_root)

    with pytest.raises(HTTPException) as exc:
        file_service.get_file_path("../outside.txt")

    assert exc.value.status_code == 400


def test_get_file_path_blocks_sibling_with_matching_string_prefix(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    sibling = tmp_path / "uploads_evil"
    sibling.mkdir()
    secret = sibling / "secret.txt"
    secret.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(file_service, "_get_upload_root", lambda: upload_root)

    with pytest.raises(HTTPException) as exc:
        file_service.get_file_path("../uploads_evil/secret.txt")

    assert exc.value.status_code == 400


def test_get_file_path_blocks_symlink_escape_when_supported(tmp_path, monkeypatch):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    link = upload_root / "tenant_1"

    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are not available on this platform")

    monkeypatch.setattr(file_service, "_get_upload_root", lambda: upload_root)

    with pytest.raises(HTTPException) as exc:
        file_service.get_file_path("tenant_1/secret.txt")

    assert exc.value.status_code == 400
