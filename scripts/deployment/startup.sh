#!/bin/bash
set -euo pipefail

# ============================================================
# Dentix Production Startup Script
#
# Production migration ownership is intentionally singular:
#   backend.scripts.preflight_migrations
#
# The preflight module owns both supported database paths:
#   - upgrade an existing Alembic-versioned PostgreSQL database
#   - bootstrap/resume a truly empty PostgreSQL database
#
# Do NOT run alembic or migration-repair helpers separately here. Keeping
# migration execution in one authority prevents ordering drift and duplicate
# migration passes during deployment startup.
# ============================================================

# Preserve the externally supplied deployment label (for example "staging")
# but force deployed containers onto the production-safe application startup
# path. Only explicit local/test environments may use legacy schema helpers.
export DENTIX_DEPLOYMENT_ENVIRONMENT="${ENVIRONMENT:-production}"
case "${DENTIX_DEPLOYMENT_ENVIRONMENT,,}" in
    development|dev|test|testing)
        export ENVIRONMENT="$DENTIX_DEPLOYMENT_ENVIRONMENT"
        ;;
    *)
        export ENVIRONMENT="production"
        ;;
esac

echo "============================================================"
echo "🚀 Dentix Production Startup — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "   Deployment label: $DENTIX_DEPLOYMENT_ENVIRONMENT | App mode: $ENVIRONMENT"
echo "============================================================"

echo ""
echo "📊 Running authoritative migration/bootstrap preflight..."
cd /app
python -m backend.scripts.preflight_migrations

echo "✅ Migration/bootstrap preflight passed."

echo ""
echo "============================================================"
echo "🌐 Starting Dentix application..."
echo "============================================================"
exec "$@"
