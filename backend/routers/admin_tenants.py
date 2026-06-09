from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
from backend import models, schemas
from backend.database import get_db
from backend.services.admin_service import AdminService
from backend.core.permissions import Role, Permission, require_permission
from backend.core.response import success_response, StandardResponse


from backend.auth import create_access_token

router = APIRouter(
    prefix="/admin/tenants",
    tags=["Admin Tenants"],
    responses={404: {"description": "Not found"}},
)


# Dependency
def require_super_admin(current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


@router.get("", response_model=StandardResponse[List[schemas.Tenant]])
def get_all_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    data = service.get_all_tenants(skip, limit)
    return success_response(data=data)


@router.put("/{tenant_id}", response_model=StandardResponse[schemas.Tenant])
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
    return success_response(data=tenant, message="Tenant updated")


@router.delete("/{tenant_id}", response_model=StandardResponse[dict])
def archive_tenant(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    tenant = service.archive_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return success_response(message="Tenant archived successfully")


@router.post("/{tenant_id}/restore", response_model=StandardResponse[dict])
def restore_tenant(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    tenant = service.restore_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return success_response(message="Tenant restored successfully")


@router.delete("/{tenant_id}/permanent", response_model=StandardResponse[dict])
def delete_tenant_permanently(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    success = service.permanently_delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return success_response(message="Tenant permanently deleted")


@router.post("/{tenant_id}/assign-plan", response_model=StandardResponse[dict])
def assign_plan_to_tenant(
    tenant_id: int,
    plan_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):

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
    return success_response(
        data={"tenant": tenant.name},
        message=f"Plan '{plan.name}' assigned successfully",
    )


# Extra: Get Tenant Users
@router.get("/{tenant_id}/users", response_model=StandardResponse[dict])
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

    return success_response(
        data={
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
    )


@router.delete("/{tenant_id}/purge-deleted-patients", response_model=StandardResponse[dict])
def purge_deleted_patients(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Permanently remove soft-deleted patients for a specific tenant."""
    # Security: If not super_admin, must belong to the tenant
    if current_user.role != Role.SUPER_ADMIN.value and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized to purge another tenant's data")
    tenant = db.query(models.Tenant).filter(
        models.Tenant.id == tenant_id,
        models.Tenant.is_deleted == False,  # noqa: E712
    ).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    deleted_patients = db.query(models.Patient).filter(
        models.Patient.tenant_id == tenant_id,
        models.Patient.is_deleted == True,  # noqa: E712
    ).all()

    count = len(deleted_patients)
    for patient in deleted_patients:
        db.delete(patient)

    db.commit()

    return success_response(
        data={"purged_count": count},
        message=f"تم حذف {count} مريض نهائياً"
    )

@router.get("/{tenant_id}/details", response_model=StandardResponse[dict])
def get_tenant_details(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AdminService(db)
    tenant = service.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    stats = service.get_tenant_detailed_stats(tenant_id)

    return success_response(data={
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "domain": tenant.domain,
            "plan": tenant.plan,
            "created_at": tenant.created_at,
            "subscription_end_date": tenant.subscription_end_date,
            "is_active": tenant.is_active,
            "contact_phone": tenant.contact_phone,
            "admin_email": next((u.email for u in tenant.users if u.role == "admin"), None)
        },
        "stats": stats
    })


@router.post("/{tenant_id}/features/{feature_key}", response_model=StandardResponse[dict])
def toggle_tenant_feature(
    tenant_id: int,
    feature_key: str,
    is_enabled: bool,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Grant or revoke a specific feature for a tenant."""
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    feature = db.query(models.FeatureFlag).filter(models.FeatureFlag.key == feature_key).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    tenant_feature = db.query(models.TenantFeature).filter(
        models.TenantFeature.tenant_id == tenant_id,
        models.TenantFeature.feature_key == feature_key
    ).first()

    if not tenant_feature:
        tenant_feature = models.TenantFeature(
            tenant_id=tenant_id,
            feature_key=feature_key,
            is_enabled=is_enabled
        )
        db.add(tenant_feature)
    else:
        tenant_feature.is_enabled = is_enabled

    db.commit()
    
    return success_response(
        data={"feature_key": feature_key, "is_enabled": is_enabled},
        message=f"Feature '{feature_key}' {'enabled' if is_enabled else 'disabled'} for tenant {tenant.name}"
    )


@router.post("/{tenant_id}/impersonate", response_model=StandardResponse[dict])
def impersonate_tenant(
    tenant_id: int,
    request: "Request",
    user_id: int = None,
    reason: str = None,
    scope: str = "read_only",
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Generate a temporary token to log in as a clinic user.
    
    Security:
    - Requires mandatory reason (audit trail)
    - Logs immutable audit record with IP, user-agent
    - Token valid for 30 minutes max
    - Default scope is read_only
    """
    import logging
    _logger = logging.getLogger("smart_clinic.impersonation")

    # 1. Require reason for audit trail
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="سبب انتحال الشخصية مطلوب (5 أحرف على الأقل) للتوثيق الأمني"
        )

    # 2. Validate scope
    allowed_scopes = {"read_only", "full_access"}
    if scope not in allowed_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"النطاق '{scope}' غير صالح. القيم المسموحة: {allowed_scopes}"
        )

    # 3. Find target user
    query = db.query(models.User).filter(
        models.User.tenant_id == tenant_id,
        models.User.is_active == True,
        models.User.is_deleted == False
    )

    if user_id:
        target_user = query.filter(models.User.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود أو غير نشط في هذه العيادة")
    else:
        target_user = query.order_by((models.User.role == Role.MANAGER.value).desc()).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="No active users found for this clinic")

    # 4. Extract request metadata for audit
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # 5. Log IMMUTABLE audit record
    _logger.warning(
        "[IMPERSONATION_START] admin_id=%s admin_username=%s target_user_id=%s "
        "target_username=%s tenant_id=%s reason='%s' scope=%s ip=%s user_agent='%s'",
        current_user.id, current_user.username,
        target_user.id, target_user.username,
        tenant_id, reason.strip(), scope,
        client_ip, user_agent[:200]
    )

    # 6. Store audit record in database (if AuditLog model exists)
    try:
        if hasattr(models, 'AuditLog'):
            audit = models.AuditLog(
                user_id=current_user.id,
                action="IMPERSONATION_START",
                entity_type="User",
                entity_id=target_user.id,
                details=(
                    f"Admin '{current_user.username}' impersonated '{target_user.username}' "
                    f"(tenant {tenant_id}). Reason: {reason.strip()}. Scope: {scope}. "
                    f"IP: {client_ip}"
                ),
                tenant_id=tenant_id,
            )
            db.add(audit)
            db.commit()
    except Exception as e:
        _logger.error("[IMPERSONATION] Audit log DB write failed: %s", e)
        # Don't block impersonation if audit log fails — the logger warning above is the backup

    # 7. Create impersonation token (30 minutes)
    access_token = create_access_token(
        data={
            "sub": target_user.username,
            "tenant_id": target_user.tenant_id,
            "role": target_user.role,
            "is_impersonating": True,
            "impersonation_scope": scope,
            "admin_id": current_user.id,
            "admin_username": current_user.username,
            "impersonation_reason": reason.strip()[:200],
        },
        expires_delta=timedelta(minutes=30)
    )

    tenant_name = target_user.tenant.name if target_user.tenant else "Unknown"

    return success_response(data={
        "access_token": access_token,
        "token_type": "bearer",
        "tenant_name": tenant_name,
        "target_user": target_user.username,
        "scope": scope,
        "expires_in_minutes": 30,
    }, message=f"تم إنشاء جلسة دخول مؤقتة لعيادة {tenant_name}")


# Required import for Request type
from starlette.requests import Request


