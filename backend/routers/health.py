"""
Health Check Router for Smart Clinic Management System.

Provides comprehensive health monitoring endpoints for:
- Basic health check
- Detailed component status
- Kubernetes liveness/readiness probes

Usage:
    GET /health - Basic check
    GET /health/detailed - Full component check (requires auth)
    GET /health/live - Kubernetes liveness
    GET /health/ready - Kubernetes readiness
"""

from fastapi import APIRouter, Depends, HTTPException
from ..core.response import success_response, error_response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import time
import os
import logging
import shutil
import psutil
from backend.database import get_async_db, engine
from backend.core.permissions import Permission, require_permission
from backend import models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])

# Track when the app started
APP_START_TIME = time.time()


# ============================================
# RESPONSE MODELS
# ============================================


class ComponentHealth(BaseModel):
    """Health status of a single component."""

    status: str  # "up" | "down" | "degraded"
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Basic health response."""

    status: str  # "healthy" | "unhealthy" | "degraded"
    version: str
    timestamp: str


class DetailedHealthResponse(BaseModel):
    """Detailed health response with component statuses."""

    status: str
    version: str
    timestamp: str
    uptime_seconds: int
    environment: str
    checks: Dict[str, ComponentHealth]


# ============================================
# HEALTH CHECK FUNCTIONS
# ============================================


async def check_database(db: AsyncSession) -> ComponentHealth:
    """Check database connectivity and latency."""
    try:
        start = time.time()
        result = (await db.execute(text("SELECT 1"))).fetchone()
        latency = (time.time() - start) * 1000

        if result:
            return ComponentHealth(
                status="up",
                latency_ms=round(latency, 2),
                message="Database connection OK",
            )
        else:
            return ComponentHealth(
                status="down", message="Database query returned no result"
            )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ComponentHealth(status="down", message=f"Database error: {str(e)}")


async def check_migrations(db: AsyncSession) -> ComponentHealth:
    """Check if database migrations are up to date."""
    try:
        # Check for required columns from latest migration
        required_columns = [
            ("materials", "category_id"),
            ("materials", "brand"),
            ("procedure_material_weights", "category_id"),
            ("treatment_material_usages", "id"),
            ("material_categories", "id"),
        ]

        missing = []
        for table, column in required_columns:
            try:
                await db.execute(text(f"SELECT {column} FROM {table} LIMIT 1"))
            except Exception:
                missing.append(f"{table}.{column}")

        if missing:
            return ComponentHealth(
                status="down",
                message=f"Migration pending: missing columns {', '.join(missing)}",
                details={"missing_columns": missing},
            )

        return ComponentHealth(
            status="up",
            message="All migrations applied",
        )
    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        return ComponentHealth(status="degraded", message=f"Migration check error: {str(e)}")


async def check_redis() -> ComponentHealth:
    """Check Redis connectivity."""
    try:
        from backend.cache import redis_client

        if redis_client is None:
            return ComponentHealth(
                status="degraded", message="Redis not configured (optional)"
            )

        start = time.time()
        pong = redis_client.ping()
        latency = (time.time() - start) * 1000

        if pong:
            info = redis_client.info("memory")
            memory_used_mb = info.get("used_memory", 0) / (1024 * 1024)

            return ComponentHealth(
                status="up",
                latency_ms=round(latency, 2),
                message="Redis connection OK",
                details={"memory_used_mb": round(memory_used_mb, 2)},
            )
        else:
            return ComponentHealth(status="down", message="Redis ping failed")
    except ImportError:
        return ComponentHealth(status="degraded", message="Redis module not available")
    except Exception as e:
        return ComponentHealth(status="down", message=f"Redis error: {str(e)}")


async def check_ai_service() -> ComponentHealth:
    """Check AI service (Groq) availability."""
    try:
        groq_key = os.getenv("GROQ_API_KEY")

        if not groq_key:
            return ComponentHealth(
                status="degraded", message="GROQ_API_KEY not configured"
            )

        # Just check if key is set, don't make actual API call
        return ComponentHealth(
            status="up", message="AI service configured", details={"provider": "groq"}
        )
    except Exception as e:
        return ComponentHealth(status="down", message=f"AI service error: {str(e)}")


async def check_disk_space() -> ComponentHealth:
    """Check available disk space."""
    try:
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        total_gb = total / (1024**3)
        usage_percent = (used / total) * 100

        if usage_percent > 95:
            status = "down"
            message = "Disk space critical (>95%)"
        elif usage_percent > 85:
            status = "degraded"
            message = "Disk space low (>85%)"
        else:
            status = "up"
            message = "Disk space OK"

        return ComponentHealth(
            status=status,
            message=message,
            details={
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "usage_percent": round(usage_percent, 1),
            },
        )
    except Exception as e:
        return ComponentHealth(
            status="degraded", message=f"Could not check disk: {str(e)}"
        )


def get_overall_status(checks: Dict[str, ComponentHealth]) -> str:
    """Determine overall health status from component checks."""
    statuses = [c.status for c in checks.values()]

    if all(s == "up" for s in statuses):
        return "healthy"
    elif any(s == "down" for s in statuses):
        return "unhealthy"
    else:
        return "degraded"


# ============================================
# ENDPOINTS
# ============================================


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if the application is running.
    """
    return HealthResponse(
        status="healthy",
        version=os.getenv("APP_VERSION", "2.0.5"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))
):
    """
    Detailed health check with component status.
    Requires authentication (admin access recommended).
    """
    # Run all checks concurrently
    database_check, migration_check, redis_check, ai_check, disk_check = await asyncio.gather(
        check_database(db),
        check_migrations(db),
        check_redis(),
        check_ai_service(),
        check_disk_space(),
        return_exceptions=True,
    )

    # Handle any exceptions from checks
    def safe_result(result, component_name):
        if isinstance(result, Exception):
            logger.error(f"{component_name} check failed: {result}")
            return ComponentHealth(status="down", message=str(result))
        return result

    checks = {
        "database": safe_result(database_check, "Database"),
        "migrations": safe_result(migration_check, "Migrations"),
        "redis": safe_result(redis_check, "Redis"),
        "ai_service": safe_result(ai_check, "AI Service"),
        "disk_space": safe_result(disk_check, "Disk Space"),
    }

    uptime = int(time.time() - APP_START_TIME)

    return DetailedHealthResponse(
        status=get_overall_status(checks),
        version=os.getenv("APP_VERSION", "2.0.5"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=uptime,
        environment=os.getenv("ENVIRONMENT", "development"),
        checks=checks,
    )


@router.get("/live")
async def liveness_probe():
    """
    Kubernetes liveness probe.
    Returns 200 if the application process is running.
    Used to determine if container should be restarted.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness_probe(db: AsyncSession = Depends(get_async_db)):
    """
    Kubernetes readiness probe.
    Returns 200 if the application is ready to receive traffic.
    Checks database connectivity.
    """
    try:
        # Quick database check
        result = (await db.execute(text("SELECT 1"))).fetchone()
        if result:
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Database not ready")
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/startup")
async def startup_check():
    """
    Startup probe for slow-starting containers.
    Returns basic info about the startup state.
    """
    uptime = int(time.time() - APP_START_TIME)
    return {
        "status": "started",
        "uptime_seconds": uptime,
        "version": os.getenv("APP_VERSION", "2.0.5"),
    }


def _ensure_not_production():
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/stress-metrics")
def get_stress_metrics():
    _ensure_not_production()
    """
    Real-time metrics for stress testing monitoring.
    Returns DB pool stats, CPU, and Memory usage.
    """
    try:
        process = psutil.Process()
        memory_info = process.memory_info()

        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "db_connections": {
                "active": engine.pool.checkedout(),
                "available": engine.pool.size() - engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "pool_size": engine.pool.size(),
            },
            "system_resources": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "memory_percent": round(process.memory_percent(), 2),
            },
        }
        return metrics
    except Exception as e:
        logger.error(f"Error fetching stress metrics: {e}")
        return success_response(data={"error": str(e)})


@router.get("/debug/procedures")
async def debug_procedures(db: AsyncSession = Depends(get_async_db)):
    _ensure_not_production()
    """
    Debug endpoint to check procedure seeding status.
    Public - no auth required for debugging.
    """
    try:
        total_procs = (await db.execute(text("SELECT COUNT(*) FROM procedures"))).scalar()
        global_procs = (await db.execute(
            text("SELECT COUNT(*) FROM procedures WHERE tenant_id IS NULL")
        )).scalar()
        tenant_count = (await db.execute(text("SELECT COUNT(*) FROM tenants"))).scalar()
        price_list_count = (await db.execute(text("SELECT COUNT(*) FROM price_lists"))).scalar()
        price_list_item_count = (await db.execute(
            text("SELECT COUNT(*) FROM price_list_items")
        )).scalar()

        return {
            "total_procedures": total_procs,
            "global_procedures": global_procs,
            "tenant_count": tenant_count,
            "price_list_count": price_list_count,
            "price_list_item_count": price_list_item_count,
        }
    except Exception as e:
        logger.error(f"Error in debug/procedures: {e}")
        return success_response(data={"error": str(e)})
