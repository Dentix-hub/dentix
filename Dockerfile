# ==========================================
# Stage 1: Build Frontend
# ==========================================
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci
COPY frontend .
RUN npm run build


# ==========================================
# Stage 2: Build Python Environment
# ==========================================
FROM python:3.11-slim AS python-deps
WORKDIR /app

# Native build tooling is isolated to the dependency builder and is never
# copied into the production runtime image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install only locked runtime dependencies. Preserve the Phase 3 security
# invariants before the environment is copied into the final image.
RUN uv sync --frozen --no-dev \
    && .venv/bin/python -c "import importlib.util; assert importlib.util.find_spec('ecdsa') is None; from jose import jwt; import chromadb; assert chromadb.__version__ == '0.6.3'; s='dentix-build-smoke-secret-32chars'; t=jwt.encode({'sub':'build'}, s, algorithm='HS256'); assert jwt.decode(t, s, algorithms=['HS256'])['sub']=='build'"


# ==========================================
# Stage 3: Production Runtime (Python)
# ==========================================
FROM python:3.11-slim AS runtime
WORKDIR /app

# Keep only runtime OS capabilities that the application actually uses.
# - libmagic1: file-content inspection support.
# - postgresql-client: pg_dump/psql power the existing backup/restore API.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Docker Spaces execute containers as uid 1000. Keep the image's
# declared user aligned with that platform contract while retaining a named
# non-root identity for local/container inspection.
RUN groupadd --gid 1000 dentix \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/dentix --shell /usr/sbin/nologin dentix

COPY --from=python-deps /app/.venv /app/.venv
COPY backend/ backend/
COPY --from=frontend-build /app/frontend/dist /app/backend/static

ENV PYTHONPATH=/app \
    ENVIRONMENT=production \
    PATH="/app/.venv/bin:${PATH}" \
    HOME=/home/dentix \
    XDG_CACHE_HOME=/home/dentix/.cache

# Only application-owned mutable paths are writable by the runtime user.
# Source code and built static assets remain root-owned/read-only.
RUN mkdir -p \
        /app/uploads \
        /app/rag_storage \
        /app/backend/static/logos \
        /app/backend/static/assets \
        /home/dentix/.cache/chroma \
        /home/dentix/.cache/huggingface \
        /home/dentix/.cache/torch \
    && chown -R dentix:dentix \
        /app/uploads \
        /app/rag_storage \
        /home/dentix

COPY scripts/deployment/startup.sh /app/startup.sh
RUN chmod 0755 /app/startup.sh

USER dentix

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/v1/health')" || exit 1

CMD ["/app/startup.sh", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
