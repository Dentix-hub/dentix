from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.orm import Session
from backend import models, crud, auth
from backend.core.limiter import limiter
from .dependencies import get_db
import logging

logger = logging.getLogger("smart_clinic")

router = APIRouter()


# --- Clinic Registration ---
@router.post("/register_clinic", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def register_clinic(
    request: Request,
    clinic_name: str = Form(...),
    admin_username: str = Form(...),
    admin_email: str = Form(...),
    admin_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Register a new clinic (Tenant) and its Admin User.
    Transactions are atomic: either both tenant and user are created, or neither.
    """
    if not clinic_name or not admin_username or not admin_password:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Check if username exists globally
    existing_user = crud.get_user(db, admin_username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check if email exists globally (optional but recommended)
    existing_email = (
        db.query(models.User).filter(models.User.email == admin_email).first()
    )
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Start Transaction
    try:
        # 1. Create Tenant
        import uuid

        domain_slug = (
            clinic_name.lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:8]
        )

        # Get Default Plan (Basic)
        default_plan = (
            db.query(models.SubscriptionPlan)
            .filter(models.SubscriptionPlan.is_default == True)
            .first()
        )
        # Fallback if no default plan
        if not default_plan:
            default_plan = db.query(models.SubscriptionPlan).first()

        plan_id = default_plan.id if default_plan else None

        new_tenant = models.Tenant(
            name=clinic_name,
            domain=domain_slug,
            is_active=True,
            subscription_plan_id=plan_id,
        )
        db.add(new_tenant)
        db.flush()  # Get ID

        # 2. Create Admin User
        hashed_password = auth.get_password_hash(admin_password)
        new_user = models.User(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            role="admin",  # First user is Admin
            tenant_id=new_tenant.id,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Generate Token for immediate login
        access_token = auth.create_access_token(
            data={
                "sub": new_user.username,
                "role": new_user.role,
                "tenant_id": new_tenant.id,
            }
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": new_user.username,
            "role": new_user.role,
            "message": "Clinic registered successfully",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
