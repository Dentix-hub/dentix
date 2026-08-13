from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_PRODUCTION_PACKAGES = {
    "bandit",
    "ddtrace",
    "ecdsa",
    "pip-audit",
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "python-jose",
    "torch",
    "sentence-transformers",
    "nvidia-cublas-cu12",
    "nvidia-cudnn-cu12",
    "cuda-toolkit",
}


def _locked_package_names() -> set[str]:
    names: set[str] = set()
    for raw_line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        assert "==" in line, f"Production dependency is not locked: {line}"
        names.add(line.split("==", 1)[0].lower())
    return names


def test_production_lock_excludes_gpu_ml_stack():
    names = _locked_package_names()
    assert not (FORBIDDEN_PRODUCTION_PACKAGES & names)
    assert not any(name.startswith(("nvidia-", "cuda-")) for name in names)


def test_production_compose_only_consumes_a_prebuilt_image():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    for service_name in ("backend", "worker", "domain-worker"):
        service = compose["services"][service_name]
        assert "build" not in service
        assert "DENTIX_IMAGE" in service["image"]


def test_droplet_pipeline_pulls_instead_of_building():
    workflow = (ROOT / ".github" / "workflows" / "cd.yml").read_text(
        encoding="utf-8"
    )
    assert "docker pull" in workflow
    assert "docker compose --project-name dentix build" not in workflow


def test_runtime_image_uses_linux_lock_and_builder_stage():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY requirements.lock" in dockerfile
    assert "FROM python:3.11-slim AS python-dependencies" in dockerfile
    assert "COPY --from=python-dependencies /install/ /usr/local/" in dockerfile
