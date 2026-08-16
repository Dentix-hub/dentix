# ==========================================
# Fast DigitalOcean Runtime (Python only)
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

# Copy requirements
COPY requirements.txt .

# Install dependencies, remove the unused pure-Python ECDSA backend, and prove
# the HS256 JWT path used by Dentix remains operational.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y ecdsa \
    && python -c "from jose import jwt; s='dentix-build-smoke-secret-32chars'; t=jwt.encode({'sub':'build'}, s, algorithm='HS256'); assert jwt.decode(t, s, algorithms=['HS256'])['sub']=='build'"

# Copy the backend code (which already contains static/ from local build)
COPY backend/ backend/

# Add /app to PYTHONPATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create necessary directories
RUN mkdir -p backend/uploads backend/static/logos && chmod -R 777 backend/uploads

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
