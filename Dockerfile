# ==========================================
# Stage 1: Build Frontend
# ==========================================
FROM node:20-alpine AS build
WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend .

# Build for production
RUN npm run build


# ==========================================
# Stage 2: Production Runtime (Python)
# ==========================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmagic1 \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root
COPY requirements.txt .

# Install dependencies. python-jose installs the pure-Python ecdsa backend even
# when the cryptography backend is selected; Dentix uses HS256, so remove that
# unused vulnerable package and immediately verify JWT encode/decode still works.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y ecdsa \
    && python -c "from jose import jwt; s='dentix-build-smoke-secret-32chars'; t=jwt.encode({'sub':'build'}, s, algorithm='HS256'); assert jwt.decode(t, s, algorithms=['HS256'])['sub']=='build'"

# Copy the backend code
COPY backend/ backend/

# Copy Frontend Build Artifacts to Backend Static Directory
# This allows FastAPI to serve the React App
COPY --from=build /app/frontend/dist /app/backend/static

# Docker deployments are production-like by default. Schema changes are handled
# by /app/startup.sh + Alembic before Uvicorn starts, never by legacy in-app
# create_all/ad-hoc migration code. A runtime environment may explicitly override
# this value when needed.
ENV PYTHONPATH=/app \
    ENVIRONMENT=production

# Create necessary persistent-data mount points
RUN mkdir -p backend/uploads backend/static/logos /app/rag_storage /root/.cache/chroma \
    && chmod -R 777 backend/uploads /app/rag_storage /root/.cache/chroma

# Copy startup script
COPY scripts/deployment/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/v1/health')" || exit 1

# Run migrations then start the application
CMD ["/app/startup.sh", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
