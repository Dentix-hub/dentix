from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import database
from ..core import migrations

router = APIRouter(prefix="/repair", tags=["Repair"])

@router.get("/schema")
def repair_schema_verbose():
    """Manually trigger schema migration with verbose output."""
    logs = []
    
    def log(msg):
        logs.append(str(msg))

    try:
        from sqlalchemy import text, inspect
        inspector = inspect(database.engine)
        
        schema_changes = []
        
        # 1. Inspect Users Table
        columns = [c['name'] for c in inspector.get_columns('users')]
        log(f"Current 'users' columns: {columns}")
        print(f"[REPAIR] Current 'users' columns: {columns}") 
        
        if 'failed_login_attempts' not in columns: schema_changes.append({"table": "users", "def": "failed_login_attempts INTEGER DEFAULT 0"})
        if 'account_locked_until' not in columns: schema_changes.append({"table": "users", "def": "account_locked_until TIMESTAMP"})
        if 'last_failed_login' not in columns: schema_changes.append({"table": "users", "def": "last_failed_login TIMESTAMP"})
        if 'is_2fa_enabled' not in columns: schema_changes.append({"table": "users", "def": "is_2fa_enabled BOOLEAN DEFAULT FALSE"})
        if 'otp_secret' not in columns: schema_changes.append({"table": "users", "def": "otp_secret VARCHAR"})
        if 'last_login' not in columns: schema_changes.append({"table": "users", "def": "last_login TIMESTAMP"}) 
        
         # 1.5 Inspect Tenants Table
        t_columns = [c['name'] for c in inspector.get_columns('tenants')]
        log(f"Current 'tenants' columns: {t_columns}")
        
        if 'logo' not in t_columns: schema_changes.append({"table": "tenants", "def": "logo VARCHAR"})
        if 'grace_period_until' not in t_columns: schema_changes.append({"table": "tenants", "def": "grace_period_until TIMESTAMP"})
        if 'auto_suspend_at' not in t_columns: schema_changes.append({"table": "tenants", "def": "auto_suspend_at TIMESTAMP"})
        if 'payment_failed_count' not in t_columns: schema_changes.append({"table": "tenants", "def": "payment_failed_count INTEGER DEFAULT 0"})
        if 'manual_override_reason' not in t_columns: schema_changes.append({"table": "tenants", "def": "manual_override_reason VARCHAR"})
        if 'last_login' not in t_columns: schema_changes.append({"table": "tenants", "def": "last_login TIMESTAMP"})
        if 'is_deleted' not in t_columns: schema_changes.append({"table": "tenants", "def": "is_deleted BOOLEAN DEFAULT FALSE"})
        if 'deleted_at' not in t_columns: schema_changes.append({"table": "tenants", "def": "deleted_at TIMESTAMP"})

        # 1.6 Inspect System Settings
        s_columns = [c['name'] for c in inspector.get_columns('system_settings')]
        log(f"Current 'system_settings' columns: {s_columns}")
        
        # 1.7 Inspect Notification Reads
        nr_columns = [c['name'] for c in inspector.get_columns('notification_reads')]
        log(f"Current 'notification_reads' columns: {nr_columns}")
        if 'is_deleted' not in nr_columns: schema_changes.append({"table": "notification_reads", "def": "is_deleted BOOLEAN DEFAULT FALSE"})

        # 1.8 Inspect Subscription Plans
        sp_columns = [c['name'] for c in inspector.get_columns('subscription_plans')]
        if 'is_ai_enabled' not in sp_columns: schema_changes.append({"table": "subscription_plans", "def": "is_ai_enabled BOOLEAN DEFAULT FALSE"})
        if 'ai_daily_limit' not in sp_columns: schema_changes.append({"table": "subscription_plans", "def": "ai_daily_limit INTEGER DEFAULT 0"})
        if 'ai_features' not in sp_columns: schema_changes.append({"table": "subscription_plans", "def": "ai_features TEXT"})

        # 1.9 Inspect Subscription Payments
        # Be careful, table name might be plural or singular depending on previous migrations, but model says 'subscription_payments'
        if 'subscription_payments' in inspector.get_table_names():
            pay_columns = [c['name'] for c in inspector.get_columns('subscription_payments')]
            log(f"Current 'subscription_payments' columns: {pay_columns}")
            if 'paid_by' not in pay_columns: schema_changes.append({"table": "subscription_payments", "def": "paid_by VARCHAR"})
        else:
            log("Table 'subscription_payments' does not exist yet (should be created by auto-migration).")

        if not schema_changes:
            log("No missing columns detected via inspection.")
            print("[REPAIR] No missing columns detected.")
        
        # 2. Add them
        with database.engine.connect() as conn:
            for change in schema_changes:
                try:
                    table_name = change["table"]
                    col_def = change["def"]
                    
                    log(f"Attempting to add to {table_name}: {col_def}")
                    print(f"[REPAIR] Adding to {table_name}: {col_def}")
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_def}"))
                    conn.commit()
                    log("SUCCESS")
                except Exception as e:
                    log(f"ERROR: {e}")
                    print(f"[REPAIR ERROR] {e}")
            
            # 3. Force auto-migration check as well
            log("Running standard auto-migration...")
            print("[REPAIR] Triggering standard migrations...")
            migrations.check_and_migrate_tables()
            log("Auto-migration finished (check console for silent errors).")

        return {"status": "completed", "logs": logs}
        
    except Exception as e:
        print(f"[REPAIR CRITICAL] {e}")
        return {"status": "critical_error", "message": str(e), "logs": logs}

@router.get("/debug-login")
def debug_login(username: str, password: str, db: Session = Depends(database.get_db)):
    """Try to replicate login logic and capture specific errors."""
    from .. import crud, models, auth
    from ..services.auth_service import AuthService
    
    logs = []
    def log(msg): logs.append(str(msg))
    
    try:
        log(f"Attempting login for: {username}")
        
        # 1. Get User
        user = crud.get_user(db, username)
        if not user:
            return {"status": "failed", "step": "get_user", "error": "User not found", "logs": logs}
        log(f"User found: {user.id} - Role: {user.role}")

        # 2. Verify Password
        if not auth.verify_password(password, user.hashed_password):
            return {"status": "failed", "step": "verify_password", "error": "Incorrect password", "logs": logs}
        log("Password verified.")

        # 3. Check System Settings (Maintenance Mode)
        try:
            maintenance = db.query(models.SystemSetting).filter(models.SystemSetting.key == "maintenance_mode").first()
            log(f"Maintenance check: {maintenance.value if maintenance else 'None'}")
        except Exception as e:
            log(f"ERROR checking SystemSetting: {e}")
            return {"status": "error", "step": "check_maintenance", "error": str(e), "logs": logs}

        # 4. Check 2FA
        log(f"2FA Enabled: {getattr(user, 'is_2fa_enabled', 'N/A')}")

        # 5. Create Session (Likely culprit)
        log("Attempting to create session...")
        try:
            access_token = "debug_token_" + str(user.id)
            AuthService.create_session(db, user.id, access_token, ip_address="127.0.0.1", user_agent="DebugTool")
            log("Session created successfully.")
        except Exception as e:
             log(f"ERROR creating session: {e}")
             return {"status": "error", "step": "create_session", "error": str(e), "logs": logs}

        return {"status": "success", "message": "Login logic verified. No 500 error detected.", "logs": logs}

    except Exception as e:
        return {"status": "critical_error", "error": str(e), "logs": logs}

@router.get("/reset-password")
def reset_password(username: str, new_password: str, db: Session = Depends(database.get_db)):
    """Force reset password for a user."""
    from .. import crud, auth
    user = crud.get_user(db, username)
    if not user:
        return {"status": "error", "message": "User not found"}
    
    try:
        hashed_pw = auth.get_password_hash(new_password)
        user.hashed_password = hashed_pw
        
        # Ensure account is active and not locked
        if hasattr(user, 'is_active'): user.is_active = True
        if hasattr(user, 'account_locked_until'): user.account_locked_until = None
        if hasattr(user, 'failed_login_attempts'): user.failed_login_attempts = 0
            
        db.commit()
        return {"status": "success", "message": f"Password reset successfully for {username}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
