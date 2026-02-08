FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (we use the frozen root requirements for stability)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files from build context (the backend folder contents) into /app/backend/
# This restores the package structure so "from . import ..." works when running as module
COPY . backend/

# Add /app to PYTHONPATH so "backend" package is importable
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p backend/uploads backend/static/logos

# Expose port
EXPOSE 7860

# Run the application using the module path
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
