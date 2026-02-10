"""
Main application entrypoint for Smart Clinic Management System.

This module sets up the FastAPI application with all necessary middleware,
dependencies, and route inclusion following separation of concerns and
modular architecture principles.
"""

from contextlib import asynccontextmanager
import os
import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
import pytz
import time
import uuid
from apscheduler.schedulers.background import BackgroundScheduler

from backend.core.config import get_cors_origins, API_V1_STR
from backend.core.limiter import limiter
from backend import models, database, auth
from backend.core import migrations, seeding
from backend.cache import get_cache_stats, invalidate_cache
from backend.middleware.security_headers import SecurityHeadersMiddleware
from backend.middleware.tenant import TenantMiddleware
from backend.middleware.error_logging import ErrorLoggingMiddleware


# sentry_sdk removed.

# Configure Sentry - DEPRECATED (Replaced by Internal Logging)
# sentry_sdk removed.

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager for startup and shutdown events."""
    print("[STARTUP] Server Starting...")

    # --- STAGING/DEV ONLY: AUTO-WIPE OPTION ---
    # To trigger: set RESET_DB_ON_STARTUP=true in environment
    # SAFETY: Blocked in PRODUCTION
    if os.getenv("RESET_DB_ON_STARTUP", "false").lower() == "true":
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production":
            print("⛔ [STARTUP] CRITICAL: DB WIPE BLOCKED IN PRODUCTION!")
        else:
            print("⚠️ [STARTUP] DEEP CLEAN DETECTED: Wiping Database...")
            try:
                models.Base.metadata.drop_all(bind=database.engine)
                models.Base.metadata.create_all(bind=database.engine)
                print("✅ [STARTUP] Database Wiped & Re-Created.")
                # Seeding will happen in step 3 below
            except Exception as e:
                print(f"❌ [STARTUP] Wipe failed: {e}")
    # --- END WIPE ---

    # 1. Create Database Tables
    try:
        models.Base.metadata.create_all(bind=database.engine)
        print("[STARTUP] Database tables verified/created.")
    except Exception as e:
        print(f"[CRITICAL] Failed to create database tables: {e}")

    # 2. Run Auto-Migrations
    try:
        print("[STARTUP] Running schema migrations...")
        migrations.check_and_migrate_tables()
    except Exception as e:
        print(f"[WARNING] Schema migration failed: {e}")

    # 3. Run Startup Schema Patches (extracted to core/startup.py)
    try:
        from backend.core.startup import run_startup_patches

        run_startup_patches()
    except Exception as e:
        print(f"[WARNING] Startup patches failed: {e}")

    # 3. Seed Initial Data
    try:
        print("[STARTUP] Seeding initial data...")
        seeding.seed_subscription_plans()
        seeding.create_first_admin()

        # Run other seeders (legacy seed.py)
        db = database.SessionLocal()
        try:
            from backend.scripts.seeds import seed

            seed.seed_data(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[ERROR] Startup seeding failed: {e}")

    # 4. FIX: Seed Global Procedures + Propagate to Tenants
    try:
        # Step 1: Create global procedures (if not exist)
        print("[STARTUP] Seeding Global Procedures...")
        from backend.scripts.seed_procedures import seed_procedures

        seed_procedures()
        print("[STARTUP] Global Procedures Seeded.")

        # Step 2: Propagate to all tenant price lists
        print("[STARTUP] Running Global Procedure Propagation...")
        from backend.scripts.fix_global_procedures import fix_global_procedures

        fix_global_procedures()
        print("[STARTUP] Global Procedure Propagation Complete.")
    except Exception as e:
        print(f"[ERROR] Global Procedure Seeding/Propagation failed: {e}")

    print("[STARTUP] System Ready.")

    yield  # Application runs here

    # Shutdown cleanup can be added here if needed


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Smart Clinic API",
    version="2.0.5",
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
print(f"[DEBUG] Loaded CORS Origins: {origins}", flush=True)
# Add Middleware (Order matters: ErrorLogging should be high up to catch everything)
app.add_middleware(ErrorLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# --- Custom Middleware ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Track request processing time and log slow requests."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.3f}"

    if process_time > 1.0:
        logger.warning(
            f"SLOW REQUEST: {request.method} {request.url.path} took {process_time:.2f}s"
        )

    return response


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add unique Trace ID to every request for debugging."""
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    request.state.trace_id = trace_id

    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response


# --- Static Files ---
base_dir = os.path.dirname(os.path.abspath(__file__))
upload_dir = os.path.join(base_dir, "uploads")
os.makedirs(upload_dir, exist_ok=True)
os.makedirs("static/logos", exist_ok=True)

app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Google Drive Scheduler ---
try:
    backend_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
    if backend_url.endswith("/"):
        backend_url = backend_url[:-1]

    from backend import google_drive_client

    # Fix: Ensure callback matches the actual router path mounted at /api/v1/settings
    from backend.core.config import API_V1_STR

    drive_client = google_drive_client.GoogleDriveClient(
        redirect_uri=f"{backend_url}{API_V1_STR}/settings/backup/callback"
    )
except Exception as e:
    print(f"WARNING: Could not initialize Google Drive Client: {e}")

    class MockDriveClient:
        def update_redirect_uri(self, *args):
            pass

        def get_auth_url(self, *args):
            return "#"

        def fetch_token(self, *args):
            raise Exception("Google Drive not configured")

    drive_client = MockDriveClient()

scheduler = BackgroundScheduler(timezone=pytz.utc)
scheduler.start()


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
# --- Register Exception Handlers ---
from backend.core.exceptions import register_exception_handlers

register_exception_handlers(app)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors nicely for debugging."""
    try:
        body = await request.json()
    except:
        body = "Could not parse body"

    print(f"\n[VALIDATION ERROR] {request.method} {request.url}")
    print(f"Body: {body}")
    print(f"Errors: {exc.errors()}\n")

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": body},
    )


app.include_router(auth.router, prefix=API_V1_STR)
app.include_router(password_reset.router, prefix=API_V1_STR)
app.include_router(patients.router, prefix=API_V1_STR)
app.include_router(treatments.router, prefix=API_V1_STR)
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


# --- Observability ---
Instrumentator().instrument(app).expose(app)


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
        or full_path.startswith("uploads")
        or full_path.startswith("auth")
    ):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not Found")

    # Serve index.html
    static_paths = [
        os.path.join(base_dir, "static", "index.html"),
        "/app/static/index.html",
    ]
    for path in static_paths:
        if os.path.exists(path):
            response = FileResponse(path)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

    return {"error": "Frontend not deployed"}


@app.on_event("startup")
async def startup_event():
    print("--- 🚀 BACKEND V3 LOADING (VERIFYING UPDATE) 🚀 ---")
    print(f"Current Working Directory: {os.getcwd()}")
    print("--- REGISTERED ROUTES ---")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"Route: {route.path}")
    print("--- END REGISTERED ROUTES ---")


# --- Protected Admin Endpoints ---
from backend.routers.auth import get_current_user


@app.post("/admin/seed-database")
def manual_seed_database(current_user=Depends(get_current_user)):
    """Manual endpoint to seed database (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")
    return seeding.manual_seed_database_logic()


# --- Debug Endpoints (Development Only) ---
if os.getenv("ENVIRONMENT", "development").lower() != "production":

    @app.get("/debug/cache-stats")
    def cache_stats():
        """Debug: check cache statistics. NOT available in production."""
        return get_cache_stats()

    @app.post("/debug/invalidate-cache")
    def clear_cache_route(prefix: str = None):
        """Debug: invalidate cache. NOT available in production."""
        invalidate_cache(prefix)
        return {"message": "Cache invalidated", "prefix": prefix}

    @app.get("/debug/db-info")
    def debug_db_info():
        """Debug: check database schema. NOT available in production."""
        from sqlalchemy import inspect

        try:
            inspector = inspect(database.engine)
            tables = inspector.get_table_names()
            return {
                "connected": True,
                "table_count": len(tables),
                "tables": tables,
            }
        except Exception:
            return {"error": "Database inspection failed"}
