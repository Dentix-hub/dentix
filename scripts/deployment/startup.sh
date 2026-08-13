#!/bin/bash
set -euo pipefail

# ============================================================
# Dentix Production Startup Script
#
# This script runs pre-flight checks BEFORE starting the app.
# If any check fails, the deployment is ABORTED (exit 1).
#
# Flow:
#   1. Run Alembic migrations (must succeed)
#   2. Verify migration health check
#   3. Start the application
# ============================================================

echo "============================================================"
echo "🚀 Dentix Production Startup — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "============================================================"

# === STEP 1: Run Alembic Migrations ===
echo ""
echo "📊 [1/2] Running Alembic migrations..."

# The historical Alembic chain predates the core schema. A brand-new database
# needs one current-model baseline before normal incremental migrations apply.
cd /app
python -m backend.scripts.init_db --if-empty

# Find alembic.ini location
ALEMBIC_DIR=""
if [ -f "/app/backend/alembic.ini" ]; then
    ALEMBIC_DIR="/app/backend"
elif [ -f "/app/alembic.ini" ]; then
    ALEMBIC_DIR="/app"
else
    echo "❌ FATAL: alembic.ini not found!"
    echo "   Searched: /app/backend/alembic.ini, /app/alembic.ini"
    exit 1
fi

cd "$ALEMBIC_DIR"
echo "   Using alembic.ini from: $ALEMBIC_DIR"

# Run alembic version repair script to clean up phantom versions
python -m backend.scripts.fix_alembic_version || true

alembic upgrade head
MIGRATION_EXIT=$?

if [ $MIGRATION_EXIT -ne 0 ]; then
    echo ""
    echo "❌ FATAL: Database migration FAILED (exit code: $MIGRATION_EXIT)"
    echo "   DEPLOYMENT ABORTED — Fix migrations before deploying."
    echo "============================================================"
    exit 1
fi

echo "✅ Migrations applied successfully."

# === STEP 2: Run Migration Health Check ===
echo ""
echo "🔍 [2/2] Running migration health check..."

cd /app
python -m backend.scripts.preflight_migrations 2>&1
HEALTH_EXIT=$?

if [ $HEALTH_EXIT -ne 0 ]; then
    echo ""
    echo "❌ FATAL: Migration health check FAILED (exit code: $HEALTH_EXIT)"
    echo "   DEPLOYMENT ABORTED — Database schema is incomplete."
    echo "============================================================"
    exit 1
fi

echo "✅ Health check passed."

# === STEP 3: Start Application ===
echo ""
echo "============================================================"
echo "🌐 Starting Dentix application..."
echo "============================================================"
exec "$@"
