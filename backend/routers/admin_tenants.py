from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend import models, schemas
from backend.database import get_db
from backend.services.admin_service import AdminService
from backend.routers.auth.dependencies import get_current_user
from backend.constants import ROLES

router = APIRouter(
    prefix="/admin/tenants",
    tags=["Admin Tenants"],
    responses={404: {"description": "Not found"}},
)


# Dependency
def require_super_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


@router.get("", response_model=List[schemas.Tenant])
def get_all_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    return service.get_all_tenants(skip, limit)


@router.put("/{tenant_id}", response_model=schemas.Tenant)
def update_tenant(
    tenant_id: int,
    tenant_update: schemas.TenantUpdate,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    tenant = service.update_tenant(
        tenant_id,
        plan=tenant_update.plan,
        is_active=tenant_update.is_active,
        subscription_end_date=tenant_update.subscription_end_date,
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.delete("/{tenant_id}")
def archive_tenant(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    tenant = service.archive_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"message": "Tenant archived successfully"}


@router.post("/{tenant_id}/restore")
def restore_tenant(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    tenant = service.restore_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"message": "Tenant restored successfully"}


@router.delete("/{tenant_id}/permanent")
def delete_tenant_permanently(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    success = service.permanently_delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"message": "Tenant permanently deleted"}


@router.post("/{tenant_id}/assign-plan")
def assign_plan_to_tenant(
    tenant_id: int,
    plan_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone, timedelta

    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan = (
        db.query(models.SubscriptionPlan)
        .filter(models.SubscriptionPlan.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    tenant.plan = plan.name
    tenant.plan_id = plan.id
    tenant.is_active = True
    tenant.subscription_end_date = datetime.now(timezone.utc) + timedelta(
        days=plan.duration_days
    )

    db.commit()
    db.refresh(tenant)
    return {
        "message": f"Plan '{plan.name}' assigned successfully",
        "tenant": tenant.name,
    }


# Extra: Get Tenant Users
@router.get("/{tenant_id}/users")
def get_tenant_users(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    tenant = service.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = service.get_users_for_tenant(tenant_id)

    # Custom Manual Schema Mapping (as seen in legacy admin.py)
    # Ideally should use Pydantic schema
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "failed_login_attempts": getattr(u, "failed_login_attempts", 0),
                "account_locked_until": str(u.account_locked_until)
                if getattr(u, "account_locked_until", None)
                else None,
            }
            for u in users
        ]
    }
