FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (we use the frozen root requirements for stability)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy all files from build context (the backend folder contents) into /app/backend/
# This restores the package structure so "from . import ..." works when running as module
COPY . backend/

# Add /app to PYTHONPATH so "backend" package is importable
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p backend/uploads backend/static/logos

# Expose port
EXPOSE 7860

# Health check for load balancer / orchestrator
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7860/api/v1/health || exit 1

# Run with gunicorn (multi-worker) for production stability
# Workers formula: (2 * CPU cores) + 1, defaulting to 4
# Timeout 120s for long AI/analytics queries
CMD ["gunicorn", "backend.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:7860", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-"]
