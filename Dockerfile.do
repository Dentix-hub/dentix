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

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code (which already contains static/ from local build)
COPY backend/ backend/

# Add /app to PYTHONPATH
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p backend/uploads backend/static/logos && chmod -R 777 backend/uploads

# Copy startup script
COPY scripts/deployment/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Expose port
EXPOSE 7860

# Run migrations then start the application
CMD ["/app/startup.sh", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
