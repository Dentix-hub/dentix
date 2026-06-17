import logging
import os
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
from backend import database, models
from backend import auth

logger = logging.getLogger(__name__)


def is_connection_error(e: Exception) -> bool:
    err_msg = str(e).lower()
    return (
        "database does not exist" in err_msg
        or "connection refused" in err_msg
        or "could not connect" in err_msg
        or "connection reset" in err_msg
    )


async def seed_default_data(db) -> None:
    """
    Seed database with initial subscription plans and default admin.
    Guarded by a PostgreSQL advisory lock to prevent concurrent seeding in multi-replica environments.
    """
    lock_acquired = True
    try:
        # Try to acquire advisory lock (non-blocking)
        # SEED_LOCK_ID = 12345
        result = await db.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": 12345}
        )
        lock_acquired = result.scalar()
    except (OperationalError, ProgrammingError) as e:
        # Expected fallback on SQLite/non-Postgres dialects
        logger.warning(f"[SEED] Advisory lock not supported/failed (expected on non-Postgres): {e}")
        lock_acquired = True

    if not lock_acquired:
        logger.info("[SEED] Seeding skipped — another instance is running it")
        return

    # 1. Subscription plans
    res = await db.execute(select(models.SubscriptionPlan))
    if not res.scalars().first():
        logger.info('[SEED] No subscription plans found. Seeding defaults...')
        plans = [
            models.SubscriptionPlan(
                name='trial',
                display_name_ar='تجريبي',
                price=0.0,
                duration_days=14,
                max_users=1,
                max_patients=50,
                features='["TRIAL", "BASIC_REPORTING"]',
                is_active=True
            ),
            models.SubscriptionPlan(
                name='basic',
                display_name_ar='أساسي',
                price=29.99,
                duration_days=30,
                max_users=2,
                max_patients=500,
                features='["BILLING", "REPORTS_BASIC"]',
                is_active=True
            ),
            models.SubscriptionPlan(
                name='pro',
                display_name_ar='محترف',
                price=79.99,
                duration_days=30,
                max_users=5,
                max_patients=2000,
                features='["BILLING", "REPORTS_ADVANCED", "LAB_INTEGRATION", "MULTI_USER"]',
                is_active=True
            ),
            models.SubscriptionPlan(
                name='enterprise',
                display_name_ar='مؤسسات',
                price=199.99,
                duration_days=30,
                max_users=None,
                max_patients=None,
                features='["BILLING", "REPORTS_ADVANCED", "LAB_INTEGRATION", "MULTI_USER", "AI_ASSISTANT"]',
                is_active=True
            )
        ]
        db.add_all(plans)
        await db.flush()
        logger.info('[SEED] Subscription plans seeded successfully.')
    else:
        logger.info('[SEED] Subscription plans already exist. Skipping.')

    # 2. Super Admin & System Tenant
    env = os.getenv("ENVIRONMENT", "development").lower()
    allow_seed = os.getenv("ALLOW_PRODUCTION_SEED", "false").lower() == "true"

    if env == "production" and not allow_seed:
        logger.info("[SEED] Seeding skipped: ENV=production and ALLOW_PRODUCTION_SEED!=true")
        return

    res_tenant = await db.execute(
        select(models.Tenant).filter(models.Tenant.name == "System Admin")
    )
    system_tenant = res_tenant.scalars().first()
    if not system_tenant:
        logger.info("[SEED] Creating System Tenant")
        system_tenant = models.Tenant(
            name="System Admin",
            subscription_status="active",
            plan="enterprise",
            is_active=True,
        )
        db.add(system_tenant)
        await db.flush()

    super_email = os.getenv('SUPER_ADMIN_EMAIL') or os.getenv("ADMIN_USERNAME") or "admin"
    super_pass = os.getenv('SUPER_ADMIN_PASSWORD') or os.getenv("ADMIN_PASSWORD")
    if not super_pass:
        if env == "production":
            logger.warning("[SEED] SUPER_ADMIN_PASSWORD not set in production. Skipping admin creation.")
            return
        else:
            logger.warning("[SEED] SUPER_ADMIN_PASSWORD not set. Using default dev password.")
            super_pass = "admin123"

    res_user = await db.execute(
        select(models.User).filter(models.User.username == super_email)
    )
    existing_user = res_user.scalars().first()
    if not existing_user:
        hashed_pwd = auth.get_password_hash(super_pass)
        admin_email = super_email if "@" in super_email else f"{super_email}@example.com"
        admin_user = models.User(
            username=super_email,
            email=admin_email,
            hashed_password=hashed_pwd,
            role="super_admin",
            tenant_id=system_tenant.id,
            is_active=True,
        )
        db.add(admin_user)
        logger.info(f"[SEED] Default super_admin created: username='{super_email}'")
    else:
        logger.info("[SEED] Admin user already exists, skipping creation.")


async def create_first_admin():
    """Ensure default admin exists for first-time setup."""
    try:
        _ctx = database.RlsContext(tenant_id=None)
        async with database.AsyncSessionLocal(context=_ctx) as _sess:
            async with _sess.bypass_rls() as db:
                super_email = os.getenv('SUPER_ADMIN_EMAIL')
                super_pass = os.getenv('SUPER_ADMIN_PASSWORD')
                if not super_email or not super_pass:
                    logger.info(
                        '[SEED] SUPER_ADMIN_EMAIL or SUPER_ADMIN_PASSWORD not set. Skipping super admin creation.'
                    )
                    return
                res = await db.execute(
                    select(models.User).filter(models.User.username == super_email)
                )
                super_admin = res.scalars().first()
                if not super_admin:
                    new_super = models.User(
                        username=super_email,
                        hashed_password=auth.get_password_hash(super_pass),
                        role='super_admin',
                        tenant_id=None
                    )
                    db.add(new_super)
                    await db.commit()
    except Exception as e:
        if is_connection_error(e):
            raise e
        logger.warning(f"[SEED WARNING] Failed to create first admin (continuing): {e}")


async def seed_subscription_plans():
    """
    Seed default subscription plans.
    Idempotent and safe: checks if table exists and plans are missing.
    """
    try:
        _ctx = database.RlsContext(tenant_id=None)
        async with database.AsyncSessionLocal(context=_ctx) as _sess:
            async with _sess.bypass_rls() as db:
                res = await db.execute(select(models.SubscriptionPlan))
                if not res.scalars().first():
                    logger.info('[SEED] No subscription plans found. Seeding defaults...')
                    plans = [
                        models.SubscriptionPlan(
                            name='trial',
                            display_name_ar='تجريبي',
                            price=0.0,
                            duration_days=7,
                            features='["TRIAL", "BASIC_REPORTING"]',
                            max_users=1,
                            max_patients=10
                        ),
                        models.SubscriptionPlan(
                            name='basic',
                            display_name_ar='أساسي',
                            price=500.0,
                            duration_days=30,
                            features='["BILLING", "REPORTS_BASIC"]',
                            max_users=1,
                            max_patients=100
                        ),
                        models.SubscriptionPlan(
                            name='pro',
                            display_name_ar='محترف',
                            price=1000.0,
                            duration_days=30,
                            features='["BILLING", "REPORTS_ADVANCED", "LAB_INTEGRATION", "MULTI_USER"]',
                            max_users=5,
                            max_patients=None
                        ),
                        models.SubscriptionPlan(
                            name='enterprise',
                            display_name_ar='مؤسسات',
                            price=2500.0,
                            duration_days=30,
                            features='["BILLING", "REPORTS_ADVANCED", "LAB_INTEGRATION", "MULTI_USER", "AI_ASSISTANT"]',
                            max_users=None,
                            max_patients=None
                        )
                    ]
                    db.add_all(plans)
                    await db.commit()
                    logger.info('[SEED] Subscription plans seeded successfully.')
                else:
                    logger.info('[SEED] Subscription plans already exist. Skipping.')
    except Exception as e:
        if is_connection_error(e):
            raise e
        logger.warning(f"[SEED WARNING] Failed to seed subscription plans (continuing): {e}")


async def manual_seed_database_logic():
    """Logic for manual seed endpoint."""
    try:
        from backend.scripts.seeds import seed
        _ctx = database.RlsContext(tenant_id=None)
        async with database.AsyncSessionLocal(context=_ctx) as _sess:
            async with _sess.bypass_rls() as db:
                # Note: seed.seed_data should be async or wrap it.
                # If seed.seed_data is sync, run it via run_sync.
                if hasattr(seed, "seed_data_async"):
                    await seed.seed_data_async(db)
                else:
                    def _sync_seed(conn):
                        from sqlalchemy.orm import Session
                        with Session(bind=conn) as sync_db:
                            seed.seed_data(sync_db)
                    await db.run_sync(_sync_seed)
        return {'message': 'Database seeding completed successfully'}
    except Exception as e:
        return {'error': str(e)}
