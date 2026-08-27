from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, timedelta, timezone
from backend import models, schemas
from backend.database import get_async_db, system_session_scope
from backend.services.admin_service import AdminService
from backend.services.subscription_renewal_service import (
    SubscriptionRenewalError,
    renew_subscription,
)
from backend.core.permissions import Role, Permission, require_permission
from backend.core.response import success_response, StandardResponse
from starlette.requests import Request


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
async def get_all_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    service = AdminService(db)
    data = await service.get_all_tenants(skip, limit)
    return success_response(data=data)


@router.put("/{tenant_id}", response_model=StandardResponse[schemas.Tenant])
async def update_tenant(
    tenant_id: int,
    tenant_update: schemas.TenantUpdate,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    service = AdminService(db)
    tenant = await service.update_tenant(
        tenant_id,
        plan=tenant_update.plan,
        is_active=tenant_update.is_active,
        subscription_end_date=tenant_update.subscription_end_date,
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return success_response(data=tenant, message="Tenant updated")


@router.post("/{tenant_id}/renew", response_model=StandardResponse[dict])
async def renew_tenant_subscription(
    tenant_id: int,
    renewal_req: schemas.TenantManualRenewalRequest,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        result = await renew_subscription(
            db,
            tenant_id=tenant_id,
            request=renewal_req,
            admin=current_user,
        )
    except SubscriptionRenewalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return success_response(data=result, message="تم تجديد الاشتراك بنجاح")


@router.delete("/{tenant_id}", response_model=StandardResponse[dict])
async def archive_tenant(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    service = AdminService(db)
    tenant = await service.archive_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return success_response(message="Tenant archived successfully")


@router.post("/{tenant_id}/restore", response_model=StandardResponse[dict])
async def restore_tenant(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    service = AdminService(db)
    tenant = await service.restore_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return success_response(message="Tenant restored successfully")


@router.delete("/{tenant_id}/permanent", response_model=StandardResponse[dict])
async def delete_tenant_permanently(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    service = AdminService(db)
    success = await service.permanently_delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return success_response(message="Tenant permanently deleted")


@router.post("/{tenant_id}/assign-plan", response_model=StandardResponse[dict])
async def assign_plan_to_tenant(
    tenant_id: int,
    plan_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    res_tenant = await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))
    tenant = res_tenant.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    res_plan = await db.execute(
        select(models.SubscriptionPlan)
        .where(models.SubscriptionPlan.id == plan_id)
    )
    plan = res_plan.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    tenant.plan = plan.name
    tenant.plan_id = plan.id
    tenant.is_active = True
    tenant.subscription_end_date = datetime.now(timezone.utc) + timedelta(
        days=plan.duration_days
    )

    await db.commit()
    await db.refresh(tenant)
    return success_response(
        data={"tenant": tenant.name},
        message=f"Plan '{plan.name}' assigned successfully",
    )


# Extra: Get Tenant Users
@router.get("/{tenant_id}/users", response_model=StandardResponse[dict])
async def get_tenant_users(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    service = AdminService(db)
    tenant = await service.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = await service.get_users_for_tenant(tenant_id)

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
async def purge_deleted_patients(
    tenant_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Permanently remove soft-deleted patients for a specific tenant."""
    # Security: If not super_admin, must belong to the tenant
    if current_user.role != Role.SUPER_ADMIN.value and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized to purge another tenant's data")

    res_tenant = await db.execute(
        select(models.Tenant).where(
            models.Tenant.id == tenant_id,
            models.Tenant.is_deleted == False,  # noqa: E712
        )
    )
    tenant = res_tenant.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    res_patients = await db.execute(
        select(models.Patient).where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == True,  # noqa: E712
        )
    )
    deleted_patients = list(res_patients.scalars().all())

    count = len(deleted_patients)
    for patient in deleted_patients:
        await db.delete(patient)

    await db.commit()

    return success_response(
        data={"purged_count": count},
        message=f"تم حذف {count} مريض نهائياً"
    )


@router.get("/{tenant_id}/details", response_model=StandardResponse[dict])
async def get_tenant_details(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    service = AdminService(db)
    stmt = select(models.Tenant).options(selectinload(models.Tenant.users)).where(models.Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    stats = await service.get_tenant_detailed_stats(tenant_id)

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
async def toggle_tenant_feature(
    tenant_id: int,
    feature_key: str,
    is_enabled: bool,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Grant or revoke a specific feature for a tenant."""
    res_tenant = await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id))
    tenant = res_tenant.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    res_feature = await db.execute(select(models.FeatureFlag).where(models.FeatureFlag.key == feature_key))
    feature = res_feature.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    res_tf = await db.execute(
        select(models.TenantFeature).where(
            models.TenantFeature.tenant_id == tenant_id,
            models.TenantFeature.feature_key == feature_key
        )
    )
    tenant_feature = res_tf.scalar_one_or_none()

    if not tenant_feature:
        tenant_feature = models.TenantFeature(
            tenant_id=tenant_id,
            feature_key=feature_key,
            is_enabled=is_enabled
        )
        db.add(tenant_feature)
    else:
        tenant_feature.is_enabled = is_enabled

    await db.commit()

    return success_response(
        data={"feature_key": feature_key, "is_enabled": is_enabled},
        message=f"Feature '{feature_key}' {'enabled' if is_enabled else 'disabled'} for tenant {tenant.name}"
    )


@router.post("/{tenant_id}/impersonate", response_model=StandardResponse[dict])
async def impersonate_tenant(
    tenant_id: int,
    request: Request,
    user_id: int = None,
    reason: str = None,
    scope: str = "read_only",
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Generate a temporary token to log in as a clinic user.
    """
    import logging
    _logger = logging.getLogger("smart_clinic.impersonation")

    if not reason or len(reason.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="سبب انتحال الشخصية مطلوب (5 أحرف على الأقل) للتوثيق الأمني"
        )

    allowed_scopes = {"read_only", "full_access"}
    if scope not in allowed_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"النطاق '{scope}' غير صالح. القيم المسموحة: {allowed_scopes}"
        )

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Impersonation is intentionally cross-tenant. Always resolve the target
    # and write its audit record through the isolated native BYPASSRLS role;
    # the ordinary request session must never gain this visibility.
    async with system_session_scope() as system_db:
        stmt = select(models.User).options(selectinload(models.User.tenant)).where(
            models.User.tenant_id == tenant_id,
            models.User.is_active == True,
            # is_deleted is nullable in legacy rows; NULL means not deleted.
            or_(models.User.is_deleted == False, models.User.is_deleted.is_(None)),
        )

        if user_id:
            stmt = stmt.where(models.User.id == user_id)
            res = await system_db.execute(stmt)
            target_user = res.scalar_one_or_none()
            if not target_user:
                raise HTTPException(
                    status_code=404,
                    detail="المستخدم غير موجود أو غير نشط في هذه العيادة",
                )
        else:
            stmt = stmt.order_by((models.User.role == Role.MANAGER.value).desc())
            res = await system_db.execute(stmt)
            target_user = res.scalars().first()
            if not target_user:
                raise HTTPException(
                    status_code=404,
                    detail="No active users found for this clinic",
                )

        target_user_id = target_user.id
        target_username = target_user.username
        target_tenant_id = target_user.tenant_id
        target_role = target_user.role
        tenant_name = target_user.tenant.name if target_user.tenant else "Unknown"

        _logger.warning(
            "[IMPERSONATION_START] admin_id=%s admin_username=%s target_user_id=%s "
            "target_username=%s tenant_id=%s reason='%s' scope=%s ip=%s user_agent='%s'",
            current_user.id,
            current_user.username,
            target_user_id,
            target_username,
            tenant_id,
            reason.strip(),
            scope,
            client_ip,
            user_agent[:200],
        )

        try:
            if hasattr(models, "AuditLog"):
                audit = models.AuditLog(
                    performed_by_id=current_user.id,
                    performed_by_username=current_user.username,
                    target_user_id=target_user_id,
                    target_username=target_username,
                    action="IMPERSONATION_START",
                    entity_type="User",
                    entity_id=target_user_id,
                    details=(
                        f"Admin '{current_user.username}' impersonated '{target_username}' "
                        f"(tenant {tenant_id}). Reason: {reason.strip()}. Scope: {scope}. "
                        f"IP: {client_ip}"
                    ),
                    tenant_id=tenant_id,
                )
                system_db.add(audit)
                await system_db.commit()
        except Exception as e:
            await system_db.rollback()
            _logger.error("[IMPERSONATION] Audit log DB write failed: %s", e)

    access_token = create_access_token(
        data={
            "sub": target_username,
            "tenant_id": target_tenant_id,
            "role": target_role,
            "is_impersonating": True,
            "impersonation_scope": scope,
            "admin_id": current_user.id,
            "admin_username": current_user.username,
            "impersonation_reason": reason.strip()[:200],
        },
        expires_delta=timedelta(minutes=30)
    )

    return success_response(data={
        "access_token": access_token,
        "token_type": "bearer",
        "tenant_name": tenant_name,
        "target_user": target_username,
        "scope": scope,
        "expires_in_minutes": 30,
    }, message=f"تم إنشاء جلسة دخول مؤقتة لعيادة {tenant_name}")
