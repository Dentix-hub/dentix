# ==========================================
# Dentix Development Runtime (Python only)
# ==========================================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmagic1 \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

# This image is an active supporting development image used by
# docker-compose.dev.yml, so include the development/test dependency group.
RUN uv sync --frozen \
    && .venv/bin/python -c "import importlib.util; assert importlib.util.find_spec('ecdsa') is None; from jose import jwt; import chromadb; assert chromadb.__version__ == '0.6.3'; s='dentix-build-smoke-secret-32chars'; t=jwt.encode({'sub':'build'}, s, algorithm='HS256'); assert jwt.decode(t, s, algorithms=['HS256'])['sub']=='build'"

COPY backend/ backend/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN mkdir -p backend/uploads backend/static/logos && chmod -R 777 backend/uploads

COPY scripts/deployment/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/v1/health')" || exit 1

CMD ["/app/startup.sh", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
