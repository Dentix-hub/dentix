import logging
import os
from sqlalchemy import text
from alembic.config import Config
from alembic import command
from backend import database

logger = logging.getLogger('smart_clinic.migrations')


def run_alembic_migrations():
    """Run Alembic migrations programmatically to the latest version."""
    try:
        logger.info("[MIGRATION] Running Alembic migrations (upgrade head)...")
        # Path to alembic.ini relative to project root
        ini_path = os.path.join(os.getcwd(), "alembic.ini")
        if not os.path.exists(ini_path):
            # Try parent dir if running from backend/
            ini_path = os.path.join(os.path.dirname(os.getcwd()), "alembic.ini")
            
        if not os.path.exists(ini_path):
            logger.error("[MIGRATION] alembic.ini not found. Skipping Alembic migrations.")
            return

        alembic_cfg = Config(ini_path)
        # Ensure it uses the current database URL
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            
        command.upgrade(alembic_cfg, "head")
        logger.info("[MIGRATION] Alembic migrations completed successfully.")
    except Exception as e:
        logger.error(f"[MIGRATION ERROR] Alembic migration failed: {e}", exc_info=True)


def run_migration_health_check():
    """Verify if critical tables and columns exist after migrations."""
    logger.info("[MIGRATION] Running migration health check...")
    checks = [
        ("materials", "category_id"),
        ("materials", "packaging_ratio"),
        ("procedure_material_weights", "current_average_usage"),
        ("treatment_material_usages", "tenant_id"),
    ]
    
    missing = []
    for table, col in checks:
        try:
            with database.engine.connect() as conn:
                # SQLite specific check (works for most, but specific for our dev/staging)
                if database.engine.name == 'sqlite':
                    res = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                    cols = [r[1] for r in res]
                    if col not in cols:
                        missing.append(f"{table}.{col}")
                else:
                    # Postgres check
                    conn.execute(text(f"SELECT {col} FROM {table} LIMIT 0"))
        except Exception:
            missing.append(f"{table}.{col}")
            
    if missing:
        logger.error(f"[MIGRATION HEALTH] Missing columns detected: {missing}")
        return False
    
    logger.info("[MIGRATION HEALTH] All critical schema components verified.")
    return True


def check_and_migrate_tables():
    """Auto-migrate schema for cloud deployments (Legacy Ad-hoc + Alembic)."""
    logger.info('[MIGRATION] Starting schema checks...')
    
    # 1. Run Alembic first (Standard way)
    run_alembic_migrations()
    
    # 2. Run Health Check
    run_migration_health_check()
    
    # 3. Run Legacy Ad-hoc migrations (Safety net)
    is_sqlite = database.engine.name == 'sqlite'
    auto_inc = ('INTEGER PRIMARY KEY AUTOINCREMENT' if is_sqlite else
        'SERIAL PRIMARY KEY')

    def add_column_safe(table, col_def):
        try:
            with database.engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_def}'))
                conn.commit()
                logger.info(
                    f"[MIGRATION] Added column '{col_def}' to '{table}'")
        except Exception as e:
            msg = str(e).lower()
            if 'duplicate column' in msg or 'already exists' in msg:
                pass
            else:
                logger.info(
                    f"[MIGRATION ERROR] Failed to add column '{col_def}' to '{table}': {e}"
                    )
    add_column_safe('treatments', 'canal_count INTEGER')
    add_column_safe('treatments', 'canal_lengths VARCHAR')
    add_column_safe('treatments', 'sessions TEXT')
    add_column_safe('treatments', 'complications TEXT')
    add_column_safe('treatments', 'doctor_id INTEGER REFERENCES users(id)')
    add_column_safe('treatments', 'tenant_id INTEGER REFERENCES tenants(id)')
    add_column_safe('payments', 'tenant_id INTEGER REFERENCES tenants(id)')
    add_column_safe('payments', 'doctor_id INTEGER REFERENCES users(id)')
    add_column_safe('attachments', 'filename VARCHAR')
    add_column_safe('attachments', 'file_type VARCHAR')
    add_column_safe('patients', 'tenant_id INTEGER REFERENCES tenants(id)')
    add_column_safe('appointments', 'tenant_id INTEGER REFERENCES tenants(id)')
    add_column_safe('users', 'tenant_id INTEGER REFERENCES tenants(id)')
    add_column_safe('users', "role VARCHAR DEFAULT 'doctor'")
    add_column_safe('tenants', 'logo VARCHAR')
    add_column_safe('tenants', 'subscription_end_date TIMESTAMP')
    add_column_safe('tenants', "plan VARCHAR DEFAULT 'trial'")
    add_column_safe('tenants', 'is_active BOOLEAN DEFAULT TRUE')
    add_column_safe('tenants', "backup_frequency VARCHAR DEFAULT 'off'")
    add_column_safe('tenants', 'google_refresh_token VARCHAR')
    add_column_safe('tenants', 'last_backup_at TIMESTAMP')
    add_column_safe('tenants', 'grace_period_until TIMESTAMP')
    add_column_safe('tenants', 'auto_suspend_at TIMESTAMP')
    add_column_safe('tenants', 'payment_failed_count INTEGER DEFAULT 0')
    add_column_safe('tenants', 'manual_override_reason VARCHAR')
    add_column_safe('tenants', 'last_login TIMESTAMP')
    add_column_safe('tenants', 'is_deleted BOOLEAN DEFAULT FALSE')
    add_column_safe('tenants', 'is_deleted BOOLEAN DEFAULT FALSE')
    add_column_safe('tenants', 'deleted_at TIMESTAMP')
    add_column_safe('tenants', 'doctor_name VARCHAR')
    add_column_safe('tenants', 'doctor_title VARCHAR')
    add_column_safe('tenants', 'clinic_address VARCHAR')
    add_column_safe('tenants', 'clinic_phone VARCHAR')
    add_column_safe('tenants', 'total_revenue FLOAT DEFAULT 0.0')
    add_column_safe('tenants', 'print_header_image VARCHAR')
    add_column_safe('tenants', 'print_footer_image VARCHAR')
    add_column_safe('subscription_plans', 'is_ai_enabled BOOLEAN DEFAULT FALSE'
        )
    add_column_safe('subscription_plans', 'ai_daily_limit INTEGER DEFAULT 0')
    add_column_safe('subscription_plans', 'ai_features TEXT')
    add_column_safe('laboratories', 'specialties VARCHAR')
    add_column_safe('lab_orders', 'work_type VARCHAR')
    add_column_safe('lab_orders', 'tooth_number VARCHAR')
    add_column_safe('lab_orders', 'shade VARCHAR')
    add_column_safe('lab_orders', 'material VARCHAR')
    add_column_safe('lab_orders', 'delivery_date TIMESTAMP')
    add_column_safe('lab_orders', 'received_date TIMESTAMP')
    add_column_safe('lab_orders', 'doctor_id INTEGER REFERENCES users(id)')
    add_column_safe('lab_orders', 'cost FLOAT DEFAULT 0.0')
    add_column_safe('lab_orders', 'price_to_patient FLOAT DEFAULT 0.0')
    add_column_safe('lab_orders', "status VARCHAR DEFAULT 'pending'")
    add_column_safe('lab_orders', 'notes TEXT')
    add_column_safe('expenses', 'tenant_id INTEGER REFERENCES tenants(id)')
    add_column_safe('users', 'commission_percent FLOAT DEFAULT 0.0')
    add_column_safe('users', 'fixed_salary FLOAT DEFAULT 0.0')
    add_column_safe('users', 'per_appointment_fee FLOAT DEFAULT 0.0')
    add_column_safe('users', 'hire_date DATE')
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS salary_payments (
                    id {auto_inc},
                    user_id INTEGER REFERENCES users(id),
                    month VARCHAR NOT NULL,
                    amount FLOAT DEFAULT 0.0,
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_partial BOOLEAN DEFAULT FALSE,
                    days_worked INTEGER,
                    notes TEXT,
                    tenant_id INTEGER REFERENCES tenants(id)
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_salary_payments_user_id ON salary_payments(user_id)'
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_salary_payments_month ON salary_payments(month)'
                ))
            conn.commit()
            logger.info("[MIGRATION] Verified table 'salary_payments'")
    except Exception as e:
        logger.info(
            f"[MIGRATION ERROR] Failed to create table 'salary_payments': {e}")
    add_column_safe('users', 'email VARCHAR')
    add_column_safe('users', 'permissions TEXT')
    add_column_safe('users', 'failed_login_attempts INTEGER DEFAULT 0')
    add_column_safe('users', 'account_locked_until TIMESTAMP')
    add_column_safe('users', 'last_failed_login TIMESTAMP')
    add_column_safe('users', 'is_2fa_enabled BOOLEAN DEFAULT FALSE')
    add_column_safe('users', 'otp_secret VARCHAR')
    add_column_safe('users', 'is_active BOOLEAN DEFAULT TRUE')
    add_column_safe('users', 'is_active BOOLEAN DEFAULT TRUE')
    add_column_safe('users', 'is_deleted BOOLEAN DEFAULT FALSE')
    add_column_safe('users', 'deleted_at TIMESTAMP')
    add_column_safe('users',
        "patient_visibility_mode VARCHAR DEFAULT 'all_assigned'")
    add_column_safe('users',
        'can_view_other_doctors_history BOOLEAN DEFAULT FALSE')
    add_column_safe('users', 'active_session_id VARCHAR')
    add_column_safe('users', 'fcm_token VARCHAR')
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id {auto_inc},
                    token VARCHAR UNIQUE NOT NULL,
                    user_id INTEGER REFERENCES users(id),
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_token ON password_reset_tokens(token)'
                ))
            conn.commit()
    except Exception as e:
        logger.info(
            f"[MIGRATION ERROR] Failed to create table 'password_reset_tokens': {e}"
            )
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS support_messages (
                    id {auto_inc},
                    user_id INTEGER REFERENCES users(id),
                    tenant_id INTEGER REFERENCES tenants(id),
                    subject VARCHAR(255),
                    message TEXT,
                    priority VARCHAR(50) DEFAULT 'normal',
                    status VARCHAR(50) DEFAULT 'unread',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_support_messages_status ON support_messages(status)'
                ))
            conn.commit()
            logger.info("[MIGRATION] Verified table 'support_messages'")
    except Exception as e:
        logger.info(
            f"[MIGRATION ERROR] Failed to create table 'support_messages': {e}"
            )
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS ai_usage_logs (
                    id {auto_inc},
                    user_id INTEGER REFERENCES users(id),
                    username VARCHAR,
                    query TEXT,
                    response_tool VARCHAR,
                    model VARCHAR,
                    response_time_ms FLOAT DEFAULT 0.0,
                    tokens_used INTEGER DEFAULT 0,
                    success BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tenant_id INTEGER REFERENCES tenants(id)
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_user_id ON ai_usage_logs(user_id)'
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_created_at ON ai_usage_logs(created_at)'
                ))
            conn.commit()
            logger.info("[MIGRATION] Verified table 'ai_usage_logs'")
    except Exception as e:
        logger.info(
            f"[MIGRATION ERROR] Failed to create table 'ai_usage_logs': {e}")
    add_column_safe('ai_usage_logs', 'model VARCHAR')
    add_column_safe('ai_usage_logs', 'trace_id VARCHAR')
    add_column_safe('ai_usage_logs', 'trace_details TEXT')
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS notifications (
                    id {auto_inc},
                    title VARCHAR,
                    content TEXT,
                    type VARCHAR DEFAULT 'info',
                    is_global BOOLEAN DEFAULT TRUE,
                    tenant_id INTEGER REFERENCES tenants(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by_id INTEGER REFERENCES users(id)
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_notifications_tenant_id ON notifications(tenant_id)'
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at)'
                ))
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS notification_reads (
                    id {auto_inc},
                    user_id INTEGER REFERENCES users(id),
                    notification_id INTEGER REFERENCES notifications(id),
                    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_notification_reads_user_id ON notification_reads(user_id)'
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_notification_reads_notification_id ON notification_reads(notification_id)'
                ))
            conn.commit()
            logger.info("[MIGRATION] Verified table 'notifications'")
    except Exception as e:
        logger.info(
            f"[MIGRATION ERROR] Failed to create table 'notifications': {e}")
    add_column_safe('notification_reads', 'is_deleted BOOLEAN DEFAULT FALSE')
    add_column_safe('subscription_payments', 'paid_by VARCHAR')
    add_column_safe('subscription_payments', 'created_by VARCHAR')
    add_column_safe('subscription_payments', 'notes TEXT')
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS saved_medications (
                    id {auto_inc},
                    tenant_id INTEGER REFERENCES tenants(id),
                    name VARCHAR NOT NULL,
                    default_dose VARCHAR,
                    notes VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_saved_medications_tenant_id ON saved_medications(tenant_id)'
                ))
            conn.commit()
            logger.info("[MIGRATION] Verified table 'saved_medications'")
    except Exception as e:
        logger.info(
            f"[MIGRATION ERROR] Failed to create table 'saved_medications': {e}"
            )
    add_column_safe('saved_medications', 'strength VARCHAR')
    add_column_safe('saved_medications', 'frequency VARCHAR')
    add_column_safe('saved_medications', 'duration VARCHAR')
    logger.info('[MIGRATION] Schema checks completed.')
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id {auto_inc},
                    user_id INTEGER REFERENCES users(id),
                    token_hash VARCHAR,
                    ip_address VARCHAR,
                    user_agent VARCHAR,
                    device_info VARCHAR,
                    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS login_history (
                    id {auto_inc},
                    user_id INTEGER REFERENCES users(id),
                    ip_address VARCHAR,
                    user_agent VARCHAR,
                    status VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS blocked_ips (
                    id {auto_inc},
                    ip_address VARCHAR UNIQUE,
                    reason VARCHAR,
                    blocked_by VARCHAR,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """
                ))
            conn.commit()
            logger.info('[MIGRATION] Verified Security Tables')
    except Exception as e:
        logger.info(f'[MIGRATION ERROR] Security tables check failed: {e}')
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS insurance_providers (
                    id {auto_inc},
                    tenant_id INTEGER REFERENCES tenants(id),
                    name VARCHAR NOT NULL,
                    code VARCHAR,
                    contact_email VARCHAR,
                    contact_phone VARCHAR,
                    address TEXT,
                    notes TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS price_lists (
                    id {auto_inc},
                    tenant_id INTEGER REFERENCES tenants(id),
                    name VARCHAR NOT NULL,
                    type VARCHAR DEFAULT 'cash',
                    description TEXT,
                    is_default BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    insurance_provider_id INTEGER REFERENCES insurance_providers(id),
                    coverage_percent FLOAT DEFAULT 100.0,
                    copay_percent FLOAT DEFAULT 0.0,
                    copay_fixed FLOAT DEFAULT 0.0,
                    effective_from DATE,
                    effective_to DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS price_list_items (
                    id {auto_inc},
                    price_list_id INTEGER REFERENCES price_lists(id),
                    procedure_id INTEGER REFERENCES procedures(id),
                    price FLOAT NOT NULL,
                    discount_percent FLOAT DEFAULT 0.0,
                    insurance_code VARCHAR,
                    max_units INTEGER,
                    requires_approval BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.commit()
            logger.info('[MIGRATION] Verified Price List Tables')
    except Exception as e:
        logger.info(f'[MIGRATION ERROR] Price List tables check failed: {e}')
    add_column_safe('patients',
        'assigned_doctor_id INTEGER REFERENCES users(id)')
    add_column_safe('patients',
        'default_price_list_id INTEGER REFERENCES price_lists(id)')
    add_column_safe('appointments', 'doctor_id INTEGER REFERENCES users(id)')
    add_column_safe('appointments',
        'price_list_id INTEGER REFERENCES price_lists(id)')
    add_column_safe('treatments',
        'price_list_id INTEGER REFERENCES price_lists(id)')
    add_column_safe('treatments', 'unit_price FLOAT')
    add_column_safe('treatments', 'price_snapshot TEXT')
    add_column_safe('materials', 'packaging_ratio FLOAT DEFAULT 1.0')
    add_column_safe('procedure_material_weights',
        'current_average_usage FLOAT DEFAULT 0.0')

    # --- INVENTORY PHASE 2: Category System & Treatment Material Tracking ---
    # Safety net for Alembic migration f1a2b3c4d5e6
    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS material_categories (
                    id {auto_inc},
                    name_en VARCHAR NOT NULL UNIQUE,
                    name_ar VARCHAR NOT NULL,
                    default_type VARCHAR DEFAULT 'DIVISIBLE',
                    default_unit VARCHAR DEFAULT 'g'
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_material_categories_id ON material_categories(id)'
                ))
            conn.commit()
            logger.info("[MIGRATION] Verified table 'material_categories'")
    except Exception as e:
        logger.info(
            f"[MIGRATION ERROR] Failed to create table 'material_categories': {e}"
            )

    add_column_safe('materials', 'category_id INTEGER REFERENCES material_categories(id)')
    add_column_safe('materials', 'brand VARCHAR')
    add_column_safe('procedure_material_weights', 'category_id INTEGER REFERENCES material_categories(id)')
    add_column_safe('procedure_material_weights', 'sample_size INTEGER DEFAULT 0')

    # Make material_id and tenant_id nullable in procedure_material_weights
    # (required for global category-level defaults)
    try:
        with database.engine.connect() as conn:
            if not is_sqlite:
                conn.execute(text(
                    'ALTER TABLE procedure_material_weights ALTER COLUMN material_id DROP NOT NULL'
                ))
                conn.execute(text(
                    'ALTER TABLE procedure_material_weights ALTER COLUMN tenant_id DROP NOT NULL'
                ))
                conn.commit()
                logger.info("[MIGRATION] Made material_id/tenant_id nullable in procedure_material_weights")
    except Exception as e:
        msg = str(e).lower()
        if 'already' in msg or 'nullable' in msg:
            pass
        else:
            logger.info(f"[MIGRATION] procedure_material_weights nullable fix: {e}")

    try:
        with database.engine.connect() as conn:
            conn.execute(text(
                f"""
                CREATE TABLE IF NOT EXISTS treatment_material_usages (
                    id {auto_inc},
                    treatment_id INTEGER NOT NULL REFERENCES treatments(id),
                    material_id INTEGER NOT NULL REFERENCES materials(id),
                    session_id INTEGER REFERENCES material_sessions(id),
                    weight_score FLOAT DEFAULT 1.0,
                    quantity_used FLOAT,
                    cost_calculated FLOAT,
                    is_manual_override BOOLEAN DEFAULT FALSE,
                    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_treatment_material_usages_id ON treatment_material_usages(id)'
                ))
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_treatment_material_usages_treatment_id ON treatment_material_usages(treatment_id)'
                ))
            conn.commit()
            logger.info("[MIGRATION] Verified table 'treatment_material_usages'")
    except Exception as e:
        logger.info(
            f"[MIGRATION ERROR] Failed to create table 'treatment_material_usages': {e}"
            )

    logger.info('[MIGRATION] Inventory Phase 2 schema checks completed.')
