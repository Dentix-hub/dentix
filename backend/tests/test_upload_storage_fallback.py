from io import BytesIO
from types import SimpleNamespace

from backend.routers import upload as upload_router


def _upload_file():
    return SimpleNamespace(file=BytesIO(b"attachment-bytes"))


def _clear_cloudinary_env(monkeypatch):
    for key in upload_router._CLOUDINARY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_partial_cloudinary_configuration_uses_local_storage(monkeypatch):
    _clear_cloudinary_env(monkeypatch)
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "configured-name-only")

    def unexpected_cloud_upload(*args, **kwargs):
        raise AssertionError("Cloudinary must not be called with partial credentials")

    monkeypatch.setattr(upload_router.cloudinary.uploader, "upload", unexpected_cloud_upload)
    monkeypatch.setattr(
        upload_router,
        "save_file_locally",
        lambda **kwargs: "tenant_7/local.png",
    )

    stored = upload_router._store_attachment_content(
        file=_upload_file(), safe_filename="safe.png", tenant_id=7
    )

    assert stored == "tenant_7/local.png"


def test_cloudinary_response_without_secure_url_falls_back_locally(monkeypatch):
    for key in upload_router._CLOUDINARY_ENV_KEYS:
        monkeypatch.setenv(key, f"value-for-{key.lower()}")

    monkeypatch.setattr(upload_router.cloudinary.uploader, "upload", lambda *a, **k: {})
    monkeypatch.setattr(
        upload_router,
        "save_file_locally",
        lambda **kwargs: "tenant_8/fallback.png",
    )

    stored = upload_router._store_attachment_content(
        file=_upload_file(), safe_filename="safe.png", tenant_id=8
    )

    assert stored == "tenant_8/fallback.png"


def test_complete_cloudinary_configuration_uses_secure_url(monkeypatch):
    for key in upload_router._CLOUDINARY_ENV_KEYS:
        monkeypatch.setenv(key, f"value-for-{key.lower()}")

    monkeypatch.setattr(
        upload_router.cloudinary.uploader,
        "upload",
        lambda *a, **k: {"secure_url": "https://cdn.example.test/attachment.png"},
    )

    def unexpected_local_save(**kwargs):
        raise AssertionError("Local storage must not run after a valid cloud upload")

    monkeypatch.setattr(upload_router, "save_file_locally", unexpected_local_save)

    stored = upload_router._store_attachment_content(
        file=_upload_file(), safe_filename="safe.png", tenant_id=9
    )

    assert stored == "https://cdn.example.test/attachment.png"
