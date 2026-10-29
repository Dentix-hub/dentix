"""HTTP contract for marketing pages served by the Hugging Face container."""

from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

import backend.main as main


@pytest.fixture
def marketing_client(tmp_path, monkeypatch):
    """Use real public documents and a temporary SPA shell, without app startup."""
    static_dir = tmp_path / "backend" / "static"
    static_dir.mkdir(parents=True)
    public_dir = Path(__file__).resolve().parents[2] / "frontend" / "public"
    for directory in ("ar", "en", "marketing"):
        shutil.copytree(public_dir / directory, static_dir / directory)
    for filename in ("robots.txt", "sitemap.xml"):
        shutil.copyfile(public_dir / filename, static_dir / filename)
    (static_dir / "index.html").write_text('<div id="root">SPA shell</div>')
    (static_dir / "sw.js").write_text("// existing service worker bootstrap")
    monkeypatch.setattr(main, "static_dir", static_dir)
    monkeypatch.setattr(main, "base_dir", static_dir.parent)
    # No lifespan context: these public requests must not need database startup.
    client = TestClient(main.app)
    yield client, static_dir
    client.close()


@pytest.mark.parametrize("language", ["ar", "en"])
def test_clean_marketing_urls_serve_real_html(marketing_client, language):
    client, static_dir = marketing_client
    response = client.get(f"/{language}?utm_source=staging")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.content == (static_dir / language / "index.html").read_bytes()
    assert f'https://www.dentixs.app/{language}' in response.text
    assert 'id="root"' not in response.text
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("language", ["ar", "en"])
@pytest.mark.parametrize("suffix", ["/", "/index.html"])
def test_marketing_aliases_redirect_once_on_same_origin(marketing_client, language, suffix):
    client, _ = marketing_client
    query = "utm_source=test&next=https%3A%2F%2Fexample.com%2F"
    response = client.get(f"/{language}{suffix}?{query}", follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == f"/{language}?{query}"
    destination = client.get(response.headers["location"])
    assert destination.status_code == 200
    assert not destination.history
    assert 'id="root"' not in destination.text


@pytest.mark.parametrize("path", [
    "/ar/unknown", "/en/unknown", "/ar/nested/index.html", "/en/missing.css",
    "/marketing/missing.css", "/marketing",
])
def test_missing_marketing_resources_are_real_404s(marketing_client, path):
    client, _ = marketing_client
    response = client.get(path)
    assert response.status_code == 404
    assert 'id="root"' not in response.text


@pytest.mark.parametrize("filename, content_types", [
    ("marketing/marketing.css", {"text/css"}),
    ("robots.txt", {"text/plain"}),
    # FileResponse uses the platform MIME database; both XML types are valid.
    ("sitemap.xml", {"text/xml", "application/xml"}),
])
def test_public_assets_keep_their_content_and_mime_type(marketing_client, filename, content_types):
    client, static_dir = marketing_client
    response = client.get(f"/{filename}")
    assert response.status_code == 200
    assert response.headers["content-type"].split(";", 1)[0] in content_types
    assert response.content == (static_dir / filename).read_bytes()


@pytest.mark.parametrize("filename", ["ar/index.html", "en/index.html", "robots.txt", "sitemap.xml"])
def test_missing_public_documents_never_return_spa_shell(marketing_client, filename):
    client, static_dir = marketing_client
    (static_dir / filename).unlink()
    url = filename.removesuffix("/index.html")
    response = client.get(f"/{url}")
    assert response.status_code == 404
    assert 'id="root"' not in response.text


def test_marketing_document_cannot_escape_static_directory(marketing_client):
    client, static_dir = marketing_client
    private_file = static_dir.parent / "private.html"
    private_file.write_text("private sentinel")
    page = static_dir / "ar" / "index.html"
    page.unlink()
    page.symlink_to(private_file)
    response = client.get("/ar")
    assert response.status_code == 404
    assert "private sentinel" not in response.text


@pytest.mark.parametrize("path", [
    "/", "/login", "/register", "/reset-password", "/patients",
    "/archive", "/enterprise", "/arbitrary", "/english", "/marketing-tools",
])
def test_application_navigation_keeps_existing_spa_behavior(marketing_client, path):
    client, static_dir = marketing_client
    response = client.get(path)
    assert response.status_code == 200
    assert response.content == (static_dir / "index.html").read_bytes()


@pytest.mark.parametrize("path", ["/api/missing", "/uploads/private.pdf", "/auth/missing"])
def test_reserved_paths_still_do_not_serve_spa(marketing_client, path):
    client, _ = marketing_client
    response = client.get(path)
    assert response.status_code == 404
    assert 'id="root"' not in response.text


def test_protected_api_still_requires_authentication(marketing_client):
    client, _ = marketing_client
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_service_worker_bootstrap_is_unchanged(marketing_client):
    client, static_dir = marketing_client
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.content == (static_dir / "sw.js").read_bytes()
    assert "no-store" in response.headers["cache-control"]
