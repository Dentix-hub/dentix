# syntax=docker/dockerfile:1.7

FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim AS python-dependencies
WORKDIR /build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_PYTHON_VERSION_WARNING=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.lock


FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/dentix

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 dentix \
    && useradd --uid 10001 --gid dentix --create-home dentix

COPY certificates/supabase-root-2021-ca.crt \
    /usr/local/share/ca-certificates/supabase-root-2021-ca.crt
RUN update-ca-certificates

COPY --from=python-dependencies /install/ /usr/local/
COPY backend/ backend/
COPY --from=frontend-build /app/frontend/dist/ /app/backend/static/
COPY scripts/deployment/startup.sh /app/startup.sh

RUN chmod 755 /app/startup.sh \
    && mkdir -p \
        /app/backend/uploads \
        /app/backend/static/logos \
        /app/rag_storage \
        /home/dentix/.cache/chroma \
    && chown -R dentix:dentix /app /home/dentix \
    && chmod 750 /app/backend/uploads /app/rag_storage

USER dentix

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/v1/health')" || exit 1

CMD ["/app/startup.sh", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
