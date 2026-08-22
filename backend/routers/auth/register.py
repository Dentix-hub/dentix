from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from backend import models, crud, schemas
from backend import auth as auth_utils
from backend.core.limiter import limiter
from backend.core.response import success_response, StandardResponse
from .dependencies import get_async_db, validate_password
import logging

logger = logging.getLogger("smart_clinic")

router = APIRouter()


# --- Clinic Registration ---
@router.post("/register_clinic", status_code=status.HTTP_201_CREATED, response_model=StandardResponse[schemas.Token])
@limiter.limit("3/minute")
async def register_clinic(
    request: Request,
    clinic_name: str = Form(...),
    admin_username: str = Form(...),
    admin_email: str = Form(...),
    admin_password: str = Form(...),
    contact_phone: str = Form(...),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Register a new clinic (Tenant) and its Admin User.
    Transactions are atomic: either both tenant and user are created, or neither.
    """
    if not clinic_name or not admin_username or not admin_password or not contact_phone:
        logger.warning(f"Registration failed: Missing fields. clinic_name={bool(clinic_name)}, user={bool(admin_username)}, pass={bool(admin_password)}, phone={bool(contact_phone)}")
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Clean inputs
    clinic_name = clinic_name.strip()
    admin_username = crud.normalize_username(admin_username)
    admin_email = admin_email.strip().lower()
    contact_phone = contact_phone.strip()

    try:
        validate_password(admin_password)
    except HTTPException as e:
        logger.warning(f"Registration failed: Password strength fail for user {admin_username}: {e.detail}")
        raise e

    # Start Transaction (all DB operations inside try/except for OperationalError)
    try:
        # Check if username exists globally (username only, NOT email)
        stmt = select(models.User).where(func.lower(models.User.username) == admin_username)
        result = await db.execute(stmt)
        existing_username = result.scalars().first()
        if existing_username:
            logger.warning(f"Registration failed: Username taken: {admin_username}")
            raise HTTPException(status_code=400, detail="Username already taken")

        # Check if email exists globally
        existing_email = await crud.get_user_by_email(db, admin_email)
        if existing_email:
            logger.warning(f"Registration failed: Email already registered: {admin_email}")
            raise HTTPException(status_code=400, detail="Email already registered")

        # 1. Create Tenant
        import uuid

        # 1. Create Tenant (domain_slug removed as it was unused)
        # Get Default Plan (Basic)
        stmt_plan = select(models.SubscriptionPlan).where(models.SubscriptionPlan.is_default)
        result_plan = await db.execute(stmt_plan)
        default_plan = result_plan.scalars().first()
        # Fallback if no default plan
        if not default_plan:
            stmt_plan_fallback = select(models.SubscriptionPlan)
            result_plan_fallback = await db.execute(stmt_plan_fallback)
            default_plan = result_plan_fallback.scalars().first()

        plan_id = default_plan.id if default_plan else None

        new_tenant = models.Tenant(
            name=clinic_name,
            is_active=True,
            plan_id=plan_id,
            contact_phone=contact_phone,
        )
        db.add(new_tenant)
        await db.flush()  # Get ID

        # 2. Create Admin User
        hashed_password = auth_utils.get_password_hash(admin_password)
        new_user = models.User(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            role="admin",  # First user is Admin
            tenant_id=new_tenant.id,
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Generate Token for immediate login
        access_token = auth_utils.create_access_token(
            data={
                "sub": new_user.username,
                "role": new_user.role,
                "tenant_id": new_tenant.id,
            }
        )

        return success_response(
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "username": new_user.username,
                "role": new_user.role,
            },
            message="Clinic registered successfully"
        )

    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning("Registration conflict: %s", type(e).__name__)
        raise HTTPException(
            status_code=409,
            detail="Username or email already registered",
        ) from e
    except OperationalError as e:
        await db.rollback()
        logger.error(f"Registration DB error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again in a moment.",
        )
    except Exception as e:
        await db.rollback()
        logger.error("Registration error: %s", type(e).__name__, exc_info=True)
        raise HTTPException(status_code=500, detail="Clinic registration failed") from e
