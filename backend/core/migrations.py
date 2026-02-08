from sqlalchemy import text
from backend import database
import logging

# Configure logger
logger = logging.getLogger("smart_clinic.migrations")

def check_and_migrate_tables():
    """Auto-migrate schema for cloud deployments."""
    print("[MIGRATION] Starting schema checks...")
    
    is_sqlite = database.engine.name == 'sqlite'
    auto_inc = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "SERIAL PRIMARY KEY"

    def add_column_safe(table, col_def):
        try:
            with database.engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
                conn.commit()
                print(f"[MIGRATION] Added column '{col_def}' to '{table}'")
        except Exception as e:
            msg = str(e).lower()
            if "duplicate column" in msg or "already exists" in msg:
                pass  # Column exists, ignore
            else:
                print(f"[MIGRATION ERROR] Failed to add column '{col_def}' to '{table}': {e}")

    # Treatments
    add_column_safe("treatments", "canal_count INTEGER")
    add_column_safe("treatments", "canal_lengths VARCHAR")
    add_column_safe("treatments", "sessions TEXT")
    add_column_safe("treatments", "complications TEXT")
    add_column_safe("treatments", "doctor_id INTEGER REFERENCES users(id)")
    add_column_safe("treatments", "tenant_id INTEGER REFERENCES tenants(id)")
    add_column_safe("payments", "tenant_id INTEGER REFERENCES tenants(id)")
    add_column_safe("payments", "doctor_id INTEGER REFERENCES users(id)")

    # Attachments
    add_column_safe("attachments", "filename VARCHAR")
    add_column_safe("attachments", "file_type VARCHAR")

    # Multi-tenancy
    add_column_safe("patients", "tenant_id INTEGER REFERENCES tenants(id)")
    add_column_safe("appointments", "tenant_id INTEGER REFERENCES tenants(id)")
    add_column_safe("users", "tenant_id INTEGER REFERENCES tenants(id)")
    add_column_safe("users", "role VARCHAR DEFAULT 'doctor'")
    add_column_safe("tenants", "logo VARCHAR")
    add_column_safe("tenants", "subscription_end_date TIMESTAMP")
    add_column_safe("tenants", "plan VARCHAR DEFAULT 'trial'")
    add_column_safe("tenants", "is_active BOOLEAN DEFAULT TRUE")
    add_column_safe("tenants", "backup_frequency VARCHAR DEFAULT 'off'")
    add_column_safe("tenants", "google_refresh_token VARCHAR")
    add_column_safe("tenants", "last_backup_at TIMESTAMP")
    # Enterprise Tenant Fields
    add_column_safe("tenants", "grace_period_until TIMESTAMP")
    add_column_safe("tenants", "auto_suspend_at TIMESTAMP")
    add_column_safe("tenants", "payment_failed_count INTEGER DEFAULT 0")
    add_column_safe("tenants", "manual_override_reason VARCHAR")
    add_column_safe("tenants", "last_login TIMESTAMP")
    add_column_safe("tenants", "is_deleted BOOLEAN DEFAULT FALSE")
    add_column_safe("tenants", "is_deleted BOOLEAN DEFAULT FALSE")
    add_column_safe("tenants", "deleted_at TIMESTAMP")
    # Rx Header Info
    add_column_safe("tenants", "doctor_name VARCHAR")
    add_column_safe("tenants", "doctor_title VARCHAR")
    add_column_safe("tenants", "clinic_address VARCHAR")
    add_column_safe("tenants", "clinic_phone VARCHAR")
    add_column_safe("tenants", "total_revenue FLOAT DEFAULT 0.0")
    add_column_safe("tenants", "print_header_image VARCHAR")
    add_column_safe("tenants", "print_footer_image VARCHAR")

    # Subscription Plans - AI Limits
    add_column_safe("subscription_plans", "is_ai_enabled BOOLEAN DEFAULT FALSE")
    add_column_safe("subscription_plans", "ai_daily_limit INTEGER DEFAULT 0")
    add_column_safe("subscription_plans", "ai_features TEXT")

    # Laboratories - Dental Lab
    add_column_safe("laboratories", "specialties VARCHAR")

    # Lab Orders - Dental Lab Work Orders
    add_column_safe("lab_orders", "work_type VARCHAR")
    add_column_safe("lab_orders", "tooth_number VARCHAR")
    add_column_safe("lab_orders", "shade VARCHAR")
    add_column_safe("lab_orders", "material VARCHAR")
    add_column_safe("lab_orders", "delivery_date TIMESTAMP")
    add_column_safe("lab_orders", "received_date TIMESTAMP")
    add_column_safe("lab_orders", "doctor_id INTEGER REFERENCES users(id)")
    add_column_safe("lab_orders", "cost FLOAT DEFAULT 0.0")
    add_column_safe("lab_orders", "price_to_patient FLOAT DEFAULT 0.0")
    add_column_safe("lab_orders", "status VARCHAR DEFAULT 'pending'")
    add_column_safe("lab_orders", "notes TEXT")

    # Expenses
    add_column_safe("expenses", "tenant_id INTEGER REFERENCES tenants(id)")

    
    # Staff compensation settings
    add_column_safe("users", "commission_percent FLOAT DEFAULT 0.0")
    add_column_safe("users", "fixed_salary FLOAT DEFAULT 0.0")
    add_column_safe("users", "per_appointment_fee FLOAT DEFAULT 0.0")
    add_column_safe("users", "hire_date DATE")
    
    # Create salary_payments table if not exists
    try:
        with database.engine.connect() as conn:
            conn.execute(text(f"""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_salary_payments_user_id ON salary_payments(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_salary_payments_month ON salary_payments(month)"))
            conn.commit()
            print("[MIGRATION] Verified table 'salary_payments'")
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to create table 'salary_payments': {e}")

    # Add email column to users
    add_column_safe("users", "email VARCHAR")
    add_column_safe("users", "permissions TEXT")
    add_column_safe("users", "failed_login_attempts INTEGER DEFAULT 0")
    add_column_safe("users", "account_locked_until TIMESTAMP")
    add_column_safe("users", "last_failed_login TIMESTAMP")
    add_column_safe("users", "is_2fa_enabled BOOLEAN DEFAULT FALSE")
    add_column_safe("users", "otp_secret VARCHAR")
    add_column_safe("users", "is_active BOOLEAN DEFAULT TRUE")
    add_column_safe("users", "is_active BOOLEAN DEFAULT TRUE")
    add_column_safe("users", "is_deleted BOOLEAN DEFAULT FALSE")
    add_column_safe("users", "deleted_at TIMESTAMP")
    
    # User - Multi-Doctor Visibility
    add_column_safe("users", "patient_visibility_mode VARCHAR DEFAULT 'all_assigned'")
    add_column_safe("users", "can_view_other_doctors_history BOOLEAN DEFAULT FALSE")
    
    # Session Security
    add_column_safe("users", "active_session_id VARCHAR")

    # Create password_reset_tokens table if not exists
    try:
        with database.engine.connect() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id {auto_inc},
                    token VARCHAR UNIQUE NOT NULL,
                    user_id INTEGER REFERENCES users(id),
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_token ON password_reset_tokens(token)"))
            conn.commit()
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to create table 'password_reset_tokens': {e}")

    # Create support_messages table if not exists
    try:
        with database.engine.connect() as conn:
            conn.execute(text(f"""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_support_messages_status ON support_messages(status)"))
            conn.commit()
            print("[MIGRATION] Verified table 'support_messages'")
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to create table 'support_messages': {e}")

    # Create ai_usage_logs table if not exists
    try:
        with database.engine.connect() as conn:
            conn.execute(text(f"""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_user_id ON ai_usage_logs(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_usage_logs_created_at ON ai_usage_logs(created_at)"))
            conn.commit()
            print("[MIGRATION] Verified table 'ai_usage_logs'")
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to create table 'ai_usage_logs': {e}")

    # Migration for existing databases
    add_column_safe("ai_usage_logs", "model VARCHAR")
    add_column_safe("ai_usage_logs", "trace_id VARCHAR")
    add_column_safe("ai_usage_logs", "trace_details TEXT")

    # Create notifications table if not exists
    try:
        with database.engine.connect() as conn:
            conn.execute(text(f"""
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
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_tenant_id ON notifications(tenant_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at)"))
            
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS notification_reads (
                    id {auto_inc},
                    user_id INTEGER REFERENCES users(id),
                    notification_id INTEGER REFERENCES notifications(id),
                    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notification_reads_user_id ON notification_reads(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notification_reads_notification_id ON notification_reads(notification_id)"))
            conn.commit()
            print("[MIGRATION] Verified table 'notifications'")
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to create table 'notifications': {e}")
    
    # Missing Columns Fixes
    add_column_safe("notification_reads", "is_deleted BOOLEAN DEFAULT FALSE")
    
    # Financial Enhancements
    add_column_safe("subscription_payments", "paid_by VARCHAR")
    add_column_safe("subscription_payments", "created_by VARCHAR")
    add_column_safe("subscription_payments", "notes TEXT")

    # Create saved_medications table if not exists
    try:
        with database.engine.connect() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS saved_medications (
                    id {auto_inc},
                    tenant_id INTEGER REFERENCES tenants(id),
                    name VARCHAR NOT NULL,
                    default_dose VARCHAR,
                    notes VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_saved_medications_tenant_id ON saved_medications(tenant_id)"))
            conn.commit()
            print("[MIGRATION] Verified table 'saved_medications'")
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to create table 'saved_medications': {e}")
        
    # Saved Medications Updates
    add_column_safe("saved_medications", "strength VARCHAR")
    add_column_safe("saved_medications", "frequency VARCHAR")
    add_column_safe("saved_medications", "duration VARCHAR")

    print("[MIGRATION] Schema checks completed.")

    # --- Security Tables Auto-Migration ---
    try:
        with database.engine.connect() as conn:
            # user_sessions
            conn.execute(text(f"""
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
            """))
            # login_history
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS login_history (
                    id {auto_inc},
                    user_id INTEGER REFERENCES users(id),
                    ip_address VARCHAR,
                    user_agent VARCHAR,
                    status VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # blocked_ips
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS blocked_ips (
                    id {auto_inc},
                    ip_address VARCHAR UNIQUE,
                    reason VARCHAR,
                    blocked_by VARCHAR,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """))
            conn.commit()
            print("[MIGRATION] Verified Security Tables")
    except Exception as e:
        print(f"[MIGRATION ERROR] Security tables check failed: {e}")

    # --- Price List Tables Auto-Migration ---
    try:
        with database.engine.connect() as conn:
            # insurance_providers
            conn.execute(text(f"""
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
            """))
            
            # price_lists
            conn.execute(text(f"""
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
            """))

            # price_list_items
            conn.execute(text(f"""
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
            """))
            conn.commit()
            print("[MIGRATION] Verified Price List Tables")
    except Exception as e:
        print(f"[MIGRATION ERROR] Price List tables check failed: {e}")

    add_column_safe("patients", "assigned_doctor_id INTEGER REFERENCES users(id)")
    add_column_safe("patients", "default_price_list_id INTEGER REFERENCES price_lists(id)")
    add_column_safe("appointments", "doctor_id INTEGER REFERENCES users(id)")
    add_column_safe("appointments", "price_list_id INTEGER REFERENCES price_lists(id)")
    add_column_safe("treatments", "price_list_id INTEGER REFERENCES price_lists(id)")
    add_column_safe("treatments", "unit_price FLOAT")
    add_column_safe("treatments", "price_snapshot TEXT")
    
    # Cost Engine / Smart Inventory
    add_column_safe("materials", "packaging_ratio FLOAT DEFAULT 1.0")
    add_column_safe("procedure_material_weights", "current_average_usage FLOAT DEFAULT 0.0")
