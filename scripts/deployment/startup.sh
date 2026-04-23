#!/bin/bash
# Startup script for Dentix backend
# Runs database migrations before starting the application

echo "🚀 Starting Dentix Deployment..."

# Run database migrations
echo "📊 Running database migrations..."
cd /app/backend || cd backend || true
alembic upgrade head
if [ $? -ne 0 ]; then
    echo "⚠️  Migration failed, but continuing startup..."
fi

# Start the application
echo "🌐 Starting application..."
exec "$@"
