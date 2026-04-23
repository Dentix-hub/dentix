# ==========================================
# Stage 1: Build Frontend
# ==========================================
FROM node:18-alpine as build
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

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY backend/ backend/

# Copy Frontend Build Artifacts to Backend Static Directory
# This allows FastAPI to serve the React App
COPY --from=build /app/frontend/dist /app/backend/static

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
