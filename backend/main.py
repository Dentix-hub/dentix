"""
Main application entrypoint for Smart Clinic Management System.

This module sets up the FastAPI application with all necessary middleware,
dependencies, and route inclusion following separation of concerns and
modular architecture principles.
"""

from contextlib import asynccontextmanager
import os
import logging
from fastapi import FastAPI, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
import time
import uuid

from backend.core.config import get_cors_origins, API_V1_STR, get_allow_origin_regex
from backend.core.limiter import limiter
from backend import models, database
from backend.core import migrations, seeding
from backend.cache import get_cache_stats, invalidate_cache
from backend.middleware.security_headers import SecurityHeadersMiddleware
from backend.middleware.tenant import TenantMiddleware
from backend.middleware.error_logging import ErrorLoggingMiddleware
from backend.core.response import success_response

# sentry_sdk removed.

# Configure Sentry - DEPRECATED (Replaced by Internal Logging)
# sentry_sdk removed.

# Configure structured logging
from backend.core.logging import setup_logging, set_trace_id
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager for startup and shutdown events."""
    logger.info("[STARTUP] Server Starting...")
    logger.info("[DEPLOY_VERIFY] DENTIX V2.0.8 IS LIVE")

    _env = os.getenv("ENVIRONMENT", "development").lower()
    _is_production = _env == "production"

    # ================================================================
    # PRODUCTION SAFETY: Schema mutation and seeding are BLOCKED
    # in production. Use Alembic via the deployment entrypoint script.
    # ================================================================
    if not _is_production:
        # --- STAGING/DEV ONLY: AUTO-WIPE OPTION ---
        if os.getenv("RESET_DB_ON_STARTUP", "false").lower() == "true":
            logger.warning("[STARTUP] DEEP CLEAN DETECTED: Wiping Database...")
            try:
                models.Base.metadata.drop_all(bind=database.engine)
                models.Base.metadata.create_all(bind=database.engine)
                logger.info("[STARTUP] Database Wiped & Re-Created.")
            except Exception:
                logger.exception("[STARTUP] Wipe failed", exc_info=True)

        # 1. Create Database Tables (DEV/STAGING ONLY)
        try:
            models.Base.metadata.create_all(bind=database.engine)
            logger.info("[STARTUP] Database tables verified/created.")
        except Exception:
            logger.exception("[STARTUP] Failed to create database tables", exc_info=True)

        # 2. Run Legacy Ad-hoc Migrations (DEV/STAGING ONLY)
        # DEPRECATED: These should be converted to Alembic revisions.
        try:
            logger.info("[STARTUP] Running legacy schema migrations...")
            migrations.check_and_migrate_tables()
        except Exception:
            logger.warning("[STARTUP] Schema migration failed", exc_info=True)

        # 3. Run Startup Schema Patches (DEV/STAGING ONLY)
        try:
            from backend.core.startup import run_startup_patches
            run_startup_patches()
        except Exception:
            logger.warning("[STARTUP] Startup patches failed", exc_info=True)

        try:
            _ctx = database.RlsContext(tenant_id=None)
            async with database.AsyncSessionLocal(context=_ctx) as _sess:
                async with _sess.bypass_rls() as db:
                    async with db.begin():
                        await seeding.seed_default_data(db)
            logger.info("Database seeding completed")
        except Exception as e:
            from sqlalchemy.exc import IntegrityError
            if isinstance(e, IntegrityError) or "unique constraint" in str(e).lower() or "uniqueviolation" in str(e).lower():
                logger.warning("Seeding skipped — data already exists")
            elif seeding.is_connection_error(e):
                logger.error("[STARTUP] Seeding connection error. Raising to restart container.")
                raise e
            else:
                logger.warning(f"Seeding failed, continuing startup: {e}")

        # 5. Seed Global Procedures + Propagate (DEV/STAGING ONLY)
        try:
            from backend.scripts.fix_procedures_tenant import fix_procedures_tenant
            from backend.scripts.seed_procedures import seed_procedures
            from backend.scripts.seed_material_categories import seed_material_categories
            from backend.scripts.seed_procedure_material_defaults import seed_procedure_material_defaults

            logger.info("[STARTUP] Converting tenant-1 procedures to global...")
            try:
                await fix_procedures_tenant()
            except Exception:
                logger.warning("[STARTUP] Failed to run fix_procedures_tenant", exc_info=True)

            logger.info("[STARTUP] Seeding Global Procedures...")
            await seed_procedures()

            logger.info("[STARTUP] Seeding Material Categories...")
            await seed_material_categories()

            logger.info("[STARTUP] Seeding Procedure-Material Defaults...")
            await seed_procedure_material_defaults()
            logger.info("[STARTUP] Global Procedures Seeded.")

            logger.info("[STARTUP] Running Global Procedure Propagation...")
            from backend.scripts.fix_global_procedures import fix_global_procedures
            await fix_global_procedures()
            logger.info("[STARTUP] Global Procedure Propagation Complete.")
        except Exception:
            logger.error("[STARTUP] Global Procedure Seeding/Propagation failed", exc_info=True)
    else:
        logger.info("[STARTUP] PRODUCTION MODE — schema mutation and seeding SKIPPED.")
        logger.info("[STARTUP] Migrations must be run via deployment entrypoint script.")

    # === ALWAYS RUN: Firebase initialization (safe, no schema changes) ===
    try:
        logger.info("[STARTUP] Initializing Firebase...")
        from backend.utils.firebase_manager import firebase_manager
        firebase_manager.initialize()
    except Exception:
        logger.error("[STARTUP] Firebase initialization failed", exc_info=True)

    logger.info("[STARTUP] System Ready.")
    logger.info("BACKEND V3 LOADED | CWD: %s | Routes: %d", os.getcwd(), len(app.routes))

    enable_workers = os.getenv("ENABLE_IN_PROCESS_WORKERS", "true").lower() == "true"
    worker_task = None
    subscription_task = None

    if enable_workers:
        import asyncio
        from backend.workers.event_processor import poll_outbox
        from backend.workers.subscription_checker import start_subscription_checker_loop
        # Start the event processor background task
        logger.info("[STARTUP] Starting Domain Event Processor...")
        worker_task = asyncio.create_task(poll_outbox(poll_interval=5))

        logger.info("[STARTUP] Starting Subscription Checker...")
        subscription_task = asyncio.create_task(start_subscription_checker_loop(interval_hours=12))

    yield  # Application runs here

    # Shutdown cleanup
    if enable_workers:
        logger.info("[SHUTDOWN] Stopping Background Workers...")
        if worker_task:
            worker_task.cancel()
        if subscription_task:
            subscription_task.cancel()
        try:
            await asyncio.gather(
                *[t for t in [worker_task, subscription_task] if t],
                return_exceptions=True
            )
        except asyncio.CancelledError:
            pass
        logger.info("[SHUTDOWN] Background Workers stopped successfully.")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Smart Clinic API",
    version="2.0.8",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- Middleware Setup ---
# 1. GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=500)

# 2. Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 3. Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Tenant Middleware (CRITICAL for data isolation)
app.add_middleware(TenantMiddleware)

# 5. CORS (Must be outermost to handle all requests)
origins = get_cors_origins()
logger.debug("[CONFIG] Loaded CORS Origins: %s", origins)
# Add Middleware (Order matters: ErrorLogging should be high up to catch everything)
app.add_middleware(ErrorLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=get_allow_origin_regex(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Trace-ID", "Accept", "Idempotency-Key", "X-CSRF-Token"],
)

# 6. CSRF Protection Middleware (for httpOnly cookie-based auth)
from backend.routers.auth.login import _validate_csrf, _CSRF_COOKIE_NAME

@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    """
    CSRF protection using double-submit cookie pattern.
    Validates CSRF token on state-changing requests (POST, PUT, DELETE, PATCH).
    Exempts: GET, HEAD, OPTIONS, auth endpoints, health checks, webhooks.
    """
    # Skip safe methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    # Skip Bearer auth requests (Authorization header contains Bearer)
    # CSRF only applies to cookie-based session auth
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return await call_next(request)


    # Skip auth endpoints (they manage their own CSRF or are entry points)
    path = request.url.path
    if request.method == "POST" and path in {
        "/api/v1/system/logs",
        "/api/v1/admin/system/logs",
    }:
        # Public, rate-limited diagnostics used before a login session exists.
        return await call_next(request)

    exempt_paths = [
        "/api/v1/auth/token",         # Login
        "/api/v1/auth/refresh",       # Token refresh
        "/api/v1/auth/logout",        # Logout
        "/api/v1/auth/login/2fa",     # 2FA login
        "/api/v1/auth/register",      # Registration
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/verify-reset-token",
        "/health",                    # Health checks
        "/api/v1/global-settings",    # Public settings
        "/api/v1/upload",             # File upload (handled separately)
        "/docs", "/redoc", "/openapi.json",  # Docs
        "/static", "/assets",         # Static files
    ]
    if any(path.startswith(p) for p in exempt_paths):
        return await call_next(request)

    # Skip webhook endpoints (they have their own validation)
    if "webhook" in path.lower() or "callback" in path.lower():
        return await call_next(request)

    # Validate CSRF token
    if not _validate_csrf(request):
        logger.warning(f"CSRF validation failed for {request.method} {path} from {request.client.host if request.client else 'unknown'}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF token validation failed. Please refresh the page and try again."}
        )

    return await call_next(request)


# --- Custom Middleware ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Track request processing time and log slow requests."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.3f}"

    # DIAGNOSTIC: Log 405 Method Not Allowed errors
    if response.status_code == 405:
        logger.error(
            f"[API_ROUTING_CONFLICT] 405 Method Not Allowed: {request.method} {request.url.path} "
            f"| Headers: {dict(request.headers)}"
        )

    if process_time > 1.0:
        logger.warning(
            f"SLOW REQUEST: {request.method} {request.url.path} took {process_time:.2f}s"
        )

    return response


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add unique Trace ID to every request for debugging and log correlation."""
    trace_id = request.headers.get("X-Trace-ID") or uuid.uuid4().hex[:12]
    request.state.trace_id = trace_id

    # Inject trace_id into structured logging context
    set_trace_id(trace_id)

    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response


# --- Static Files ---
import pathlib
project_root = pathlib.Path(__file__).resolve().parent.parent
base_dir = project_root / "backend"
upload_dir = project_root / "uploads"
# Check both /app/static and /app/backend/static
static_dir = base_dir / "static" if (base_dir / "static").exists() else project_root / "static"

os.makedirs(upload_dir, exist_ok=True)
os.makedirs(static_dir / "logos", exist_ok=True)
os.makedirs(static_dir / "assets", exist_ok=True)

# SECURITY: /uploads is NOT mounted publicly. Files are served through
# authenticated endpoints in routers/upload.py (GET /upload/file/{path})
# This prevents unauthorized access to patient files (PHI).
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")


from backend.core.startup import init_drive_client
drive_client = init_drive_client()

# --- Include Routers ---
from backend.routers import (
    auth,
    patients,
    appointments,
    users,
    treatments,
    payments,
    expenses,
    laboratories,
    settings,
    procedures,
    dashboard,
    notifications,
    ai,
    ai_admin,
    ai_assist,
    support,
    admin_tenants,
    admin_subscriptions,
    admin_system,  # New Modular Admin Routers
    system_admin,  # Compatibility Layer for Super Admin
    admin_audit,   # B3.1: Audit logs + system logs
    admin_stats,   # B3.1: Dashboard stats
    admin_security,
    admin_features,
    repair,
    accounting,
    password_reset,
    medications,
    prescriptions,
    analytics_ai_v2,
    health,
    admin_doctors,  # Health checks + Multi-Doctor Management
    price_lists,
    insurance,
    attachments,
    system_logs,  # Price Lists, Insurance, Attachments, System Logs
    inventory,  # Inventory System
    inventory_smart,  # Smart Inventory Suggestions
    financials,  # Smart Costing & Financials
    metrics,  # Metrics & Profitability
)

# --- Register Exception Handlers ---
from backend.core.exceptions import register_exception_handlers

from backend.routers.auth.dependencies import get_current_user

@app.get("/api/auth/session")
async def get_session_direct_root(
    current_user: models.User = Depends(get_current_user)
):
    """Direct root endpoint to get current authenticated user's session details."""
    from backend.core.response import success_response
    return success_response(data={
        "id": current_user.id,
        "name": current_user.full_name or current_user.username,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
    })


app.include_router(treatments.router, prefix=API_V1_STR)

app.include_router(patients.router, prefix=API_V1_STR)
app.include_router(auth.router, prefix=f"{API_V1_STR}/auth")
app.include_router(password_reset.router, prefix=f"{API_V1_STR}/auth")
app.include_router(appointments.router, prefix=API_V1_STR)
app.include_router(users.router, prefix=API_V1_STR)
app.include_router(payments.router, prefix=API_V1_STR)
app.include_router(expenses.router, prefix=API_V1_STR)
app.include_router(laboratories.router, prefix=API_V1_STR)
app.include_router(settings.router, prefix=API_V1_STR)
app.include_router(procedures.router, prefix=API_V1_STR)
app.include_router(dashboard.router, prefix=API_V1_STR)
app.include_router(notifications.router, prefix=API_V1_STR)
app.include_router(admin_tenants.router, prefix=API_V1_STR)
app.include_router(admin_subscriptions.router, prefix=API_V1_STR)
app.include_router(admin_system.router, prefix=API_V1_STR)
app.include_router(system_admin.router, prefix=API_V1_STR)
app.include_router(admin_audit.router, prefix=API_V1_STR)   # B3.1: Audit & system logs
app.include_router(admin_stats.router, prefix=API_V1_STR)   # B3.1: Dashboard stats
app.include_router(admin_security.router, prefix=API_V1_STR)
app.include_router(admin_features.router, prefix=API_V1_STR)
# app.include_router(admin_subscriptions.router, prefix=API_V1_STR) # Already included above
# app.include_router(admin.router, prefix=f"{API_V1_STR}/admin", tags=["admin"]) # Deprecated
app.include_router(
    system_logs.router, prefix=f"{API_V1_STR}/system/logs", tags=["system-logs"]
)
app.include_router(analytics_ai_v2.router, prefix=API_V1_STR)
app.include_router(ai.router, prefix=API_V1_STR)
app.include_router(ai_admin.router, prefix=API_V1_STR)
app.include_router(ai_assist.router, prefix=API_V1_STR)
app.include_router(support.router, prefix=API_V1_STR)
if os.getenv("ENVIRONMENT", "development").lower() != "production":
    app.include_router(repair.router, prefix=API_V1_STR)
app.include_router(accounting.router, prefix=API_V1_STR)
app.include_router(medications.router, prefix=API_V1_STR)
app.include_router(prescriptions.router, prefix=API_V1_STR)
app.include_router(health.router, prefix=API_V1_STR)  # Health check endpoints
app.include_router(
    admin_doctors.router, prefix=API_V1_STR
)  # Multi-Doctor visibility management
app.include_router(price_lists.router, prefix=API_V1_STR)  # Multi Price List
app.include_router(insurance.router, prefix=API_V1_STR)  # Insurance Providers
app.include_router(attachments.router, prefix=API_V1_STR)  # Attachments (Delete)
from backend.routers import upload

app.include_router(upload.router, prefix=API_V1_STR)
app.include_router(inventory.router, prefix=API_V1_STR)
app.include_router(inventory_smart.router, prefix=API_V1_STR)
app.include_router(financials.router, prefix=API_V1_STR)
app.include_router(metrics.router, prefix=API_V1_STR)


# --- Global Settings (public, no auth) ---
@app.get(f"{API_V1_STR}/global-settings")
async def get_global_settings(db: AsyncSession = Depends(database.get_async_db)):
    """Return global application settings (banner, support info, etc.)."""
    from sqlalchemy import select

    # Helper to get setting from DB or fallback to ENV
    async def get_setting(key, env_name, default=""):
        try:
            stmt = select(models.SystemSetting).filter(models.SystemSetting.key == key)
            result = await db.execute(stmt)
            val = result.scalars().first()
            if val and val.value:
                return val.value
        except Exception as e:
            logger.error(f"Error fetching setting {key}: {e}")
        return os.getenv(env_name, default)

    return success_response({
        "banner": await get_setting("global_announcement", "GLOBAL_BANNER", None),
        "support_email": await get_setting("support_email", "SUPPORT_EMAIL", "support@smartdentalclinicapp.com"),
        "support_phone": await get_setting("support_phone", "SUPPORT_PHONE", "+20 120 130 1415"),
        "support_whatsapp": await get_setting("support_whatsapp", "SUPPORT_WHATSAPP", "201201301415"),
        "support_working_hours": await get_setting("support_working_hours", "SUPPORT_WORKING_HOURS", "9:00 AM - 10:00 PM"),
    })


# --- Observability ---
# Workaround for compatibility issue between FastAPI >=0.110.0 and prometheus-fastapi-instrumentator.
# Newer FastAPI versions include nested APIRouter instances as _IncludedRouter in app.routes,
# which lack the 'path' attribute expected by the instrumentator.
for route in app.routes:
    if not hasattr(route, "path"):
        route.path = ""

Instrumentator().instrument(app).expose(app)


# --- Static File Serving Protection ---
def get_safe_static_path(base_directory: pathlib.Path, requested_path_str: str) -> pathlib.Path | None:
    """
    Safely joins a base directory with a requested path string,
    preventing path traversal and other injection attacks.
    """
    if not requested_path_str:
        return None

    # 1. Disallow null bytes
    if "\0" in requested_path_str:
        logger.warning(f"SECURITY: Null byte detected in path: {requested_path_str}")
        return None

    # 2. Strip leading slashes/backslashes to prevent absolute path escapes on join
    clean_path = requested_path_str.lstrip("/\\")

    try:
        # 3. Join and resolve to canonical path
        base_resolved = base_directory.resolve()
        full_path = (base_resolved / clean_path).resolve()

        # 4. Verify the resulting path is still within the base directory
        if full_path.is_relative_to(base_resolved):
            return full_path

        logger.warning(f"SECURITY: Path traversal attempt blocked: {requested_path_str}")
    except Exception as e:
        logger.error(f"Error resolving path {requested_path_str}: {e}")

    return None


# --- System Routes ---
# Note: /health is now handled by health.router with more comprehensive checks


from fastapi.responses import FileResponse

# ...


@app.get("/")
async def read_root():
    """Serve the React Frontend."""
    # Check both potential static locations
    static_paths = [
        os.path.join(base_dir, "static", "index.html"),  # Local dev /app/backend/static
        "/app/static/index.html",  # Docker /app/static
    ]

    for path in static_paths:
        if os.path.exists(path):
            return FileResponse(path)

    return {
        "message": "Welcome to Smart Clinic API (Frontend not found)",
        "version": "2.0.0",
        "docs": "/docs",
    }


# SPA Catch-all route (must be last)
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Serve React App for any unknown path (SPA support)."""
    # Exclude API/Static paths and auth endpoints
    if (
        full_path.startswith("api")
        or full_path.startswith("static")
        or full_path.startswith("assets")
        or full_path.startswith("uploads")
        or full_path.startswith("auth")
    ):
        if full_path.endswith("/"):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"/{full_path.rstrip('/')}", status_code=307)

        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")

    # Check if the file exists in the static directory (e.g. /logo.png)
    # Using path safety utility to prevent path traversal
    safe_file_path = get_safe_static_path(static_dir, full_path)

    if safe_file_path and safe_file_path.is_file():
        return FileResponse(str(safe_file_path))

    # Serve index.html for SPA routing
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        response = FileResponse(index_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return {"error": "Frontend not deployed"}
