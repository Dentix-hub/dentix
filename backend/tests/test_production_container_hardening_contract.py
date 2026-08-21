from pathlib import Path


DOCKERFILE = Path(__file__).resolve().parents[2] / "Dockerfile"


def _dockerfile_text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _runtime_stage() -> str:
    marker = "FROM python:3.11-slim AS runtime"
    text = _dockerfile_text()
    assert marker in text, "Production runtime stage must remain explicit"
    return text.split(marker, 1)[1]


def test_runtime_is_non_root_and_hugging_face_compatible():
    runtime = _runtime_stage()

    assert "useradd --uid 1000" in runtime
    assert "USER dentix" in runtime
    assert runtime.index("USER dentix") < runtime.index("CMD [")


def test_runtime_excludes_native_build_toolchain():
    runtime = _runtime_stage()

    assert "gcc \\" not in runtime
    assert "g++ \\" not in runtime
    assert "libpq-dev" not in runtime
    assert "COPY --from=python-deps /app/.venv /app/.venv" in runtime


def test_runtime_preserves_required_os_capabilities():
    runtime = _runtime_stage()

    assert "libmagic1" in runtime
    assert "postgresql-client" in runtime


def test_runtime_writable_paths_are_app_owned_without_world_writable_permissions():
    text = _dockerfile_text()
    runtime = _runtime_stage()

    assert "chmod -R 777" not in text
    assert "/root/.cache" not in text
    assert "/app/uploads" in runtime
    assert "/app/rag_storage" in runtime
    assert "HOME=/home/dentix" in runtime
    assert "XDG_CACHE_HOME=/home/dentix/.cache" in runtime
    assert "chown -R dentix:dentix" in runtime


def test_runtime_uses_frozen_virtual_environment_on_path():
    runtime = _runtime_stage()

    assert 'PATH="/app/.venv/bin:${PATH}"' in runtime
    assert "uv sync --frozen --no-dev" not in runtime
