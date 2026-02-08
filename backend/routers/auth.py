"""
print("DEBUG: LOADING BACKEND.ROUTERS.AUTH MODULE")
Authentication Router
Handles login, registration, and user profile endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import os
import uuid
import shutil

from .. import models, schemas, crud, auth, database
from ..services.auth_service import AuthService
from ..constants import ROLES
from backend.core.limiter import limiter

# Create limiter instance for this router
# Uses global instance now

router = APIRouter(prefix="", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def validate_password(password: str) -> bool:
    """
    Validate password strength.
    Requirements: min 6 chars, at least one letter AND one number.
    """
    if len(password) < 6:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    return has_letter and has_number


def get_db():
    """Database session dependency."""
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """Validate JWT token and return current user."""
    from datetime import datetime, timezone
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(f"DEBUG: Decoding token: {token[:10]}...") 
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        print(f"DEBUG: Payload decoded: {payload}")
        username: str = payload.get("sub")
        tenant_id: int = payload.get("tenant_id")
        if username is None:
            print("DEBUG: Username is None")
            raise credentials_exception
        token_data = schemas.TokenData(username=username, tenant_id=tenant_id)
    except auth.JWTError as e:
        print(f"DEBUG: JWT Decode Error: {e}")
        # DEBUG: Add server time and token exp to error details
        try:
             # Decode without verification to get claims
             unsafe_payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM], options={"verify_signature": False, "verify_exp": False})
             exp_claim = unsafe_payload.get("exp")
             server_time_utc = datetime.now(timezone.utc)
             server_time_ts = server_time_utc.timestamp()
             debug_info = f" | Server Time: {server_time_utc} ({server_time_ts}) | Token Exp: {exp_claim} | Diff: {float(exp_claim) - server_time_ts if exp_claim else 'N/A'}"
        except Exception:
             debug_info = " | Could not extract debug info"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT Error: {str(e)}{debug_info}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"DEBUG: Unexpected Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth Error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validated User
    user = crud.get_user(db, username=token_data.username)
    if user is None:
        print(f"DEBUG: User not found in DB for username: {token_data.username}")
        # Debug: list all users
        all_users = db.query(models.User).all()
        print(f"DEBUG: All users in DB: {[u.username for u in all_users]}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User not found: {token_data.username}",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # SINGLE SESSION POLICY: Validate Session ID
    token_sid = payload.get("sid")
    # Use getattr to prevent crash if column hasn't migrated yet
    active_session_val = getattr(user, 'active_session_id', None)
    
    if token_sid and active_session_val:
        if token_sid != active_session_val:
            print(f"DEBUG: Session Mismatch. Token: {token_sid}, DB: {active_session_val}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="تم تسجيل الدخول من جهاز آخر. يرجى إعادة تسجيل الدخول.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Check Tenant Subscription
    if user.tenant and user.role != ROLES.SUPER_ADMIN:
        if not user.tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is inactive",
            )

        if (
            user.tenant.subscription_end_date
            and user.tenant.subscription_end_date < datetime.utcnow()
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Subscription expired"
            )

    return user


# --- Debug Endpoint ---
@router.get("/debug-token")
def debug_token_validation(token: str, db: Session = Depends(get_db)):
    """Debug endpoint to validate a token manually and see the error."""
    try:
        from datetime import datetime
        print(f"DEBUG: Validating token: {token}")
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username = payload.get("sub")
        
        user = crud.get_user(db, username=username)
        if not user:
            return {"valid": False, "error": "User not found in DB", "payload": payload}
            
        return {
            "valid": True, 
            "username": username, 
            "role": user.role, 
            "user_id": user.id,
            "tenant_id": user.tenant_id
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}

@router.get("/debug-auth-info")
def debug_auth_info(db: Session = Depends(get_db)):
    """Debug endpoint to check DB and Schema status."""
    try:
        from sqlalchemy import text
        # Check connection
        db.execute(text("SELECT 1"))
        
        # Check Tables
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        
        # Check Users
        user_count = db.query(models.User).count()
        first_user = db.query(models.User).first()
        
        # Check Columns in User
        user_cols = []
        if first_user:
            user_cols = list(first_user.__dict__.keys())

        return {
            "status": "ok", 
            "db_connected": True, 
            "tables": tables,
            "user_count": user_count,
            "sample_user_has_2fa": hasattr(first_user, 'is_2fa_enabled') if first_user else False,
            "user_cols_raw": str(user_cols)
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/debug/ping")
def debug_ping():
    """Simple ping to verify router is active."""
    return {"message": "pong", "router": "auth"}

@router.get("/debug/manual-db")
def debug_manual_db():
    """Manually create session to test DB connection without Depends()."""
    try:
        from backend.database import SessionLocal
        db = SessionLocal()
        try:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            return {"status": "ok", "message": "Manual DB Session Successful"}
        finally:
            db.close()
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

# --- Login ---
@router.post("/token", response_model=schemas.Token)
@limiter.limit("1000/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    try:
        """Authenticate user and return JWT token."""
        # 1. Fetch User safely
        try:
            user = crud.get_user(db, form_data.username)
        except Exception as db_err:
            print(f"[LOGIN ERROR] DB Error fetching user: {db_err}")
            raise HTTPException(status_code=500, detail="Database connection error")

        # 2. Verify Credentials
        # Use explicit check to distinguish generic errors from bad password
        is_valid = False
        try:
            if user:
                is_valid = auth.verify_password(form_data.password, user.hashed_password)
        except Exception as hash_err:
            print(f"[LOGIN ERROR] Password Hashing Error: {hash_err}")
            # Don't crash, just deny
            is_valid = False

        if not user or not is_valid:
            # OPTIONAL: Differentiate for debugging if needed, but security best practice is generic.
            # However, user asked for "Wrong Password".
            # We will stick to the standard message but ensure it's reached.
            print(f"[LOGIN FAILED] User: {form_data.username} - Invalid Credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="اسم المستخدم أو كلمة الصفحة غير صحيحة", # Translated to Arabic for better UX
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check for Global Maintenance Mode
        if user.role != ROLES.SUPER_ADMIN:
            maintenance_mode = db.query(models.SystemSetting).filter(models.SystemSetting.key == "maintenance_mode").first()
            if maintenance_mode and maintenance_mode.value.lower() == "true":
                 raise HTTPException(
                    status_code=503,
                    detail="System is currently under maintenance. Please try again later."
                )

        # Check for Account Deactivation
        if hasattr(user, 'is_active') and not user.is_active:
             raise HTTPException(
                status_code=403,
                detail="Your account has been disabled. Please contact support."
            )

        # SECURITY: Check Tenant Status (Soft Delete / Inactive)
        # Fixes issue where deleted tenants could still login
        if user.role != ROLES.SUPER_ADMIN:
             if not user.tenant:
                 # Clean up orphan users or just block them
                 raise HTTPException(
                     status_code=403,
                     detail="Account not linked to any active clinic."
                 )
             
             if user.tenant.is_deleted:
                 raise HTTPException(
                     status_code=403,
                     detail="This clinic account has been deleted."
                 )
             if not user.tenant.is_active:
                 raise HTTPException(
                     status_code=403,
                     detail="Clinic account is inactive. Please contact support."
                 )

        # 2FA CHECK
        # Use getattr to be safe against missing columns in staging
        is_2fa = getattr(user, 'is_2fa_enabled', False)
        secret = getattr(user, 'otp_secret', None)
        
        if is_2fa and secret:
            temp_token = auth.create_access_token(
                data={"sub": user.username, "scope": "2fa_pending"},
                expires_delta=auth.timedelta(minutes=5)
            )
            return {"access_token": temp_token, "token_type": "bearer", "user_status": "2fa_required"}

        # Create Tokens
        import uuid
        session_id = str(uuid.uuid4())
        
        # SINGLE SESSION POLICY: Update user with new session ID
        user.active_session_id = session_id
        db.commit()
        
        access_token = auth.create_access_token(
            data={
                "sub": user.username, 
                "role": user.role, 
                "tenant_id": user.tenant_id,
                "sid": session_id # Session ID Claim
            }
        )
        refresh_token = auth.create_refresh_token(
            data={"sub": user.username, "sid": session_id}
        )
        
        # SINGLE SESSION POLICY: Invalidate all previous sessions for this user
        try:
            # This prevents the same account from being used on multiple devices simultaneously
            db.query(models.UserSession).filter(
                models.UserSession.user_id == user.id,
                models.UserSession.is_active == True
            ).update({"is_active": False})
            
            # Record Session (with Refresh Token)
            AuthService.create_session(
                db, user.id, refresh_token, 
                ip_address=request.client.host, 
                user_agent=request.headers.get('user-agent'),
                device_info=session_id # Store session ID in device info for tracking
            )
        except Exception as session_error:
            # Fallback if UserSessions table doesn't exist or other DB error
            print(f"[ERROR] Session Management Failed: {session_error}")
        
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "refresh_token": refresh_token,
            "role": user.role,
            "username": user.username
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return the error detail to the client for debugging
        raise HTTPException(
            status_code=500,
            detail=f"DEBUG ERROR: {str(e)}"
        )

@router.get("/debug/fix-schema")
@router.get("/auth/debug/fix-schema")
def fix_staging_schema(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    """Force run schema fixes for staging (GET for easy browser access)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    results = []
    try:
        from sqlalchemy import text
        # 1. Fix Appointments doctor_id and price_list_id
        try:
            db.execute(text("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS doctor_id INTEGER REFERENCES users(id);"))
            results.append("Added doctor_id to appointments")
        except Exception as e:
            results.append(f"appointments doctor_id fix failed: {e}")

        try:
            db.execute(text("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS price_list_id INTEGER REFERENCES price_lists(id);"))
            results.append("Added price_list_id to appointments")
        except Exception as e:
            results.append(f"appointments price_list_id fix failed: {e}")

        # 2. Fix Patients columns
        try:
            db.execute(text("ALTER TABLE patients ADD COLUMN IF NOT EXISTS assigned_doctor_id INTEGER REFERENCES users(id);"))
            results.append("Added assigned_doctor_id to patients")
        except Exception as e:
            results.append(f"patients assigned_doctor_id fix failed: {e}")

        try:
            db.execute(text("ALTER TABLE patients ADD COLUMN IF NOT EXISTS default_price_list_id INTEGER REFERENCES price_lists(id);"))
            results.append("Added default_price_list_id to patients")
        except Exception as e:
            results.append(f"patients default_price_list_id fix failed: {e}")

        # 3. Fix Users columns
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS patient_visibility_mode VARCHAR DEFAULT 'all_assigned';"))
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_other_doctors_history BOOLEAN DEFAULT FALSE;"))
            # New Session Security
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_session_id VARCHAR;"))
            results.append("Added user visibility and session columns")
        except Exception as e:
            results.append(f"users fix failed: {e}")

        # 4. Fix Treatments columns (Pricing)
        try:
            db.execute(text("ALTER TABLE treatments ADD COLUMN IF NOT EXISTS price_list_id INTEGER REFERENCES price_lists(id);"))
            db.execute(text("ALTER TABLE treatments ADD COLUMN IF NOT EXISTS unit_price FLOAT;"))
            db.execute(text("ALTER TABLE treatments ADD COLUMN IF NOT EXISTS price_snapshot TEXT;"))
            results.append("Added pricing columns to treatments")
        except Exception as e:
            results.append(f"treatments fix failed: {e}")

        # 5. Fix Subscription Plans
        try:
            # Check dialect to ensure correct syntax (Postgres/SQLite)
            # SQLite doesn't support IF NOT EXISTS in ALTER TABLE ADD COLUMN usually, but let's try standard SQL or catch error
            # For robustness we can catch the "duplicate column" error
            try:
                db.execute(text("ALTER TABLE subscription_plans ADD COLUMN is_default BOOLEAN DEFAULT FALSE;"))
                results.append("Added is_default to subscription_plans")
            except Exception as inner_e:
                if "duplicate column" in str(inner_e).lower() or "no such table" in str(inner_e).lower():
                     results.append(f"subscription_plans fix note: {inner_e}")
                else:
                     # Retry for SQLite which might not like DEFAULT FALSE in some versions or just fallback
                     results.append(f"subscription_plans fix might already exist or failed: {inner_e}")

        except Exception as e:
            results.append(f"subscription_plans fix critical fail: {e}")
            
        db.commit()
        return {"status": "fixed", "details": results}
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}


@router.post("/auth/refresh", response_model=schemas.Token)
def refresh_token(
    refresh_token: str = Form(...),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Exchange refresh token for new access token."""
    try:
        payload = auth.jwt.decode(refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        if payload.get("type") != "refresh":
             raise HTTPException(status_code=401, detail="Invalid token type")
        username = payload.get("sub")
    except auth.JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Validate Session
    session = AuthService.get_session_by_token(db, refresh_token)
    if not session:
         raise HTTPException(status_code=401, detail="Session expired or revoked")

    user = crud.get_user(db, username)
    if not user:
         raise HTTPException(status_code=401, detail="User not found")

    # Issue new Access Token
    new_access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    
    return {"access_token": new_access_token, "token_type": "bearer", "refresh_token": refresh_token}



# --- 2FA & Session Endpoints ---

@router.post("/auth/2fa/login", response_model=schemas.Token)
def login_2fa(
    code: str = Form(...),
    token: str = Depends(oauth2_scheme), # Temp token from first step
    db: Session = Depends(get_db),
    request: Request = None
):
    """Complete login with 2FA Code using the temp token."""
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username = payload.get("sub")
        scope = payload.get("scope")
        if scope != "2fa_pending":
             raise HTTPException(status_code=401, detail="Invalid login flow")
    except Exception:
         raise HTTPException(status_code=401, detail="Invalid session")

    user = crud.get_user(db, username)
    if not user:
         raise HTTPException(status_code=401, detail="User not found")

    if not AuthService.verify_2fa_code(user.otp_secret, code):
         raise HTTPException(status_code=400, detail="Invalid OTP Code")

    # Success - Issue real token
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    AuthService.create_session(
        db, user.id, access_token, 
        ip_address=request.client.host if request else "unknown", 
        user_agent=request.headers.get('user-agent')
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/2fa/setup")
def setup_2fa(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a secret for 2FA setup."""
    secret = AuthService.generate_2fa_secret(current_user)
    return {"secret": secret, "otpauth_url": f"otpauth://totp/SmartClinic:{current_user.username}?secret={secret}&issuer=SmartClinic"}

@router.post("/auth/2fa/verify")
def verify_2fa_setup(
    code: str,
    secret: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm 2FA setup with a code."""
    if AuthService.enable_2fa(db, current_user, secret, code):
        return {"message": "2FA Enabled Successfully"}
    raise HTTPException(status_code=400, detail="Verification Failed")

@router.get("/auth/sessions")
def get_sessions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AuthService.get_user_sessions(db, current_user.id)

@router.delete("/auth/sessions/{session_id}")
def revoke_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if AuthService.revoke_session(db, session_id, current_user.id):
        return {"message": "Session revoked"}
    raise HTTPException(status_code=404, detail="Session not found")


# --- User Profile ---
@router.put("/users/me", response_model=schemas.User)

def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    if user_update.username and user_update.username != current_user.username:
        if crud.get_user(db, user_update.username):
            raise HTTPException(status_code=400, detail="Username already registered")
        current_user.username = user_update.username

    if user_update.password:
        if not validate_password(user_update.password):
            raise HTTPException(
                status_code=400, 
                detail="كلمة المرور يجب أن تحتوي على 6 أحرف على الأقل، مع حرف ورقم"
            )
        current_user.hashed_password = auth.get_password_hash(user_update.password)

    if user_update.email:
        current_user.email = user_update.email

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/users/me/", response_model=schemas.User)
def get_user_me(current_user: models.User = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user


from backend.services.cache_service import cached

# --- Public System Settings ---
@router.get("/global-settings")
@cached(key_prefix="public_settings", expire=600)  # Cache for 10 minutes
def get_public_settings(db: Session = Depends(get_db)):
    """Fetch public system settings (e.g. Banner)."""
    settings = db.query(models.SystemSetting).filter(
        models.SystemSetting.key.in_([
            "global_announcement", 
            "support_phone", 
            "support_whatsapp", 
            "support_email",
            "support_working_hours"
        ])
    ).all()
    
    settings_dict = {s.key: s.value for s in settings}
    
    return {
        "banner": settings_dict.get("global_announcement", ""),
        "support_phone": settings_dict.get("support_phone", ""),
        "support_whatsapp": settings_dict.get("support_whatsapp", ""),
        "support_email": settings_dict.get("support_email", ""),
        "support_working_hours": settings_dict.get("support_working_hours", "")
    }


# --- Clinic Registration ---
@router.post("/auth/register_clinic", response_model=schemas.Token)
def register_clinic(
    clinic_name: str = Form(...),
    admin_username: str = Form(...),
    admin_email: str = Form(...),
    admin_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Register a new clinic with admin user."""
    # RELAXED: Allow duplicate clinic names
    # if crud.get_tenant_by_name(db, clinic_name):
    #    raise HTTPException(status_code=400, detail=f"Clinic name '{clinic_name}' already registered")
    
    # RELAXED: Allow duplicate usernames, enforce Email Uniqueness
    # if crud.get_user(db, admin_username):
    #     raise HTTPException(status_code=400, detail=f"Username '{admin_username}' already taken")
    
    if crud.get_user_by_email(db, admin_email):
         raise HTTPException(status_code=400, detail=f"Email '{admin_email}' already registered")
    
    # Check email format
    if "@" not in admin_email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    # Validate password strength
    if not validate_password(admin_password):
        raise HTTPException(
            status_code=400, 
            detail="كلمة المرور يجب أن تحتوي على 6 أحرف على الأقل، مع حرف ورقم"
        )

    try:
        # 1. Find Default Plan
        default_plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.is_default == True).first()
        
        tenant_data = {
            "name": clinic_name,
            "subscription_status": "active" if default_plan else "trial",
        }
        
        if default_plan:
            tenant_data["plan_id"] = default_plan.id
            tenant_data["plan"] = default_plan.name # Legacy field support
            # Set end date based on duration
            from datetime import datetime, timedelta
            tenant_data["subscription_end_date"] = datetime.utcnow() + timedelta(days=default_plan.duration_days)
            
        tenant = models.Tenant(**tenant_data)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        hashed_password = auth.get_password_hash(admin_password)
        new_user = models.User(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            role="admin",
            tenant_id=tenant.id,
        )
        db.add(new_user)
        db.commit()

        # --- Auto-Create Default Price List & Populate ---
        try:
            # 1. Create Default Price List
            default_price_list = models.PriceList(
                tenant_id=tenant.id,
                name="كاش",
                type="cash",
                is_default=True,
                is_active=True
            )
            db.add(default_price_list)
            db.commit()
            db.refresh(default_price_list)
            
            # 2. Fetch Global Procedures
            global_procs = db.query(models.Procedure).filter(models.Procedure.tenant_id == None).all()
            
            # 3. Populate List Items
            for proc in global_procs:
                 item = models.PriceListItem(
                     price_list_id=default_price_list.id,
                     procedure_id=proc.id,
                     price=proc.price or 0.0
                 )
                 db.add(item)
            
            db.commit()
            print(f"Initialized Default Price List for Tenant {tenant.id} with {len(global_procs)} procedures.")
            
        except Exception as pl_error:
            print(f"Failed to initialize price list: {pl_error}")
            # Non-critical, continue registration

        access_token = auth.create_access_token(
            data={
                "sub": new_user.username,
                "role": new_user.role,
                "tenant_id": new_user.tenant_id,
            }
        )
        refresh_token = auth.create_refresh_token(
            data={"sub": new_user.username}
        )
        
        # Record Session
        # client_host = request.client.host if request else "unknown" (need to add request param or default)
        # For now, we'll try to add Request param to function signature in a separate edit or just use defaults if cleaner, 
        # but let's stick to the minimal fix first: Return the token.
        # Ideally we should create session too.
        
        AuthService.create_session(
            db, new_user.id, refresh_token,
            ip_address="registration", # Simplified as we don't have request obj yet
            user_agent="web-client"
        )
        
        return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
