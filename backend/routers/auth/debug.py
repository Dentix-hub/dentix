from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend import models, schemas, crud, auth
from .dependencies import get_db, get_current_user
from sqlalchemy import text
import traceback

router = APIRouter()


# --- Debug Endpoints ---
@router.get("/debug-token")
def debug_token_validation(token: str, db: Session = Depends(get_db)):
    """Debug endpoint to validate a token manually and see the error."""
    try:
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
            "tenant_id": user.tenant_id,
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.get("/debug-auth-info")
def debug_auth_info(db: Session = Depends(get_db)):
    """Debug endpoint to check DB and Schema status."""
    try:
        # Check connection
        db.execute(text("SELECT 1"))

        # Check Tables
        # Simple cross-db compatible check
        try:
            # SQLite
            result = db.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result]
        except:
            # Postgres
            result = db.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
            )
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
            "sample_user_has_2fa": hasattr(first_user, "is_2fa_enabled")
            if first_user
            else False,
            "user_cols_raw": str(user_cols),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


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
            db.execute(text("SELECT 1"))
            return {"status": "ok", "message": "Manual DB Session Successful"}
        finally:
            db.close()
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@router.get("/debug/fix-schema")
@router.get("/auth/debug/fix-schema")
def fix_staging_schema(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Force run schema fixes for staging (GET for easy browser access)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    results = []
    try:
        # 1. Fix Appointments doctor_id and price_list_id
        try:
            db.execute(
                text(
                    "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS doctor_id INTEGER REFERENCES users(id);"
                )
            )
            results.append("Added doctor_id to appointments")
        except Exception as e:
            results.append(f"appointments doctor_id fix failed: {e}")

        try:
            db.execute(
                text(
                    "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS price_list_id INTEGER REFERENCES price_lists(id);"
                )
            )
            results.append("Added price_list_id to appointments")
        except Exception as e:
            results.append(f"appointments price_list_id fix failed: {e}")

        # 2. Fix Patients columns
        try:
            db.execute(
                text(
                    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS assigned_doctor_id INTEGER REFERENCES users(id);"
                )
            )
            results.append("Added assigned_doctor_id to patients")
        except Exception as e:
            results.append(f"patients assigned_doctor_id fix failed: {e}")

        try:
            db.execute(
                text(
                    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS default_price_list_id INTEGER REFERENCES price_lists(id);"
                )
            )
            results.append("Added default_price_list_id to patients")
        except Exception as e:
            results.append(f"patients default_price_list_id fix failed: {e}")

        db.commit()
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

    return {"status": "ok", "results": results}
