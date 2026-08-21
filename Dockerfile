# ==========================================
# Stage 1: Build Frontend
# ==========================================
FROM node:20-alpine AS build
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci
COPY frontend .
RUN npm run build


# ==========================================
# Stage 2: Production Runtime (Python)
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# Phase 3 intentionally preserves the existing runtime system package set.
# Builder/runtime separation and non-root hardening are handled independently
# in Phase 4 so dependency normalization remains reversible and reviewable.
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmagic1 \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Pinned uv binary + canonical dependency inputs.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

# Production installs runtime dependencies only. `ecdsa` is excluded by the
# canonical uv resolver policy in pyproject.toml; verify the JWT path immediately.
RUN uv sync --frozen --no-dev \
    && .venv/bin/python -c "import importlib.util; assert importlib.util.find_spec('ecdsa') is None; from jose import jwt; import chromadb; assert chromadb.__version__ == '0.6.3'; s='dentix-build-smoke-secret-32chars'; t=jwt.encode({'sub':'build'}, s, algorithm='HS256'); assert jwt.decode(t, s, algorithms=['HS256'])['sub']=='build'"

COPY backend/ backend/
COPY --from=build /app/frontend/dist /app/backend/static

ENV PYTHONPATH=/app \
    ENVIRONMENT=production \
    PATH="/app/.venv/bin:${PATH}"

RUN mkdir -p backend/uploads backend/static/logos /app/rag_storage /root/.cache/chroma \
    && chmod -R 777 backend/uploads /app/rag_storage /root/.cache/chroma

COPY scripts/deployment/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/v1/health')" || exit 1

CMD ["/app/startup.sh", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
