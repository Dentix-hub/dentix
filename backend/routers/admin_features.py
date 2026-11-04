import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from backend import models, schemas
from backend.database import get_async_db
from backend.services.feature_service import FeatureFlagService
from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    canonicalize_capability_key,
)
from backend.core.permissions import Role
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse


router = APIRouter(
    prefix="/admin/features",
    tags=["Admin Features"],
    responses={404: {"description": "Not found"}},
)


# Dependency to check for super admin (Reuse from security router or move to common)
def get_super_admin(current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    # Allow 'super_admin' OR 'admin' with no tenant
    if current_user.role == Role.SUPER_ADMIN.value:
        return current_user

    if current_user.role == Role.ADMIN.value and current_user.tenant_id is None:
        return current_user

    raise HTTPException(status_code=403, detail="Not authorized")


@router.get("", response_model=List[schemas.FeatureFlag])
async def get_all_flags(
    db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(get_super_admin)
):
    return await FeatureFlagService.get_all_flags(db)


@router.post("", response_model=schemas.FeatureFlag)
async def create_flag(
    flag: schemas.FeatureFlagCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    return await FeatureFlagService.create_flag(db, flag)


@router.post("/override", response_model=schemas.TenantFeature)
async def set_tenant_override(
    override: schemas.TenantFeatureOverride,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    return await FeatureFlagService.set_tenant_override(
        db, override.tenant_id, override.feature_key, override.is_enabled
    )


@router.delete("/override")
async def delete_tenant_override(
    tenant_id: Optional[int] = None,
    feature_key: Optional[str] = None,
    payload: Optional[schemas.TenantFeatureOverrideDelete] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    target_tenant_id = tenant_id if tenant_id is not None else (payload.tenant_id if payload else None)
    target_key = feature_key if feature_key is not None else (payload.feature_key if payload else None)
    if target_tenant_id is None or not target_key:
        raise HTTPException(status_code=422, detail="tenant_id and feature_key are required")
    deleted = await FeatureFlagService.delete_tenant_override(db, target_tenant_id, target_key)
    return {"status": "success", "deleted": deleted}


@router.get("/tenant/{tenant_id}/{feature_key}")
async def get_tenant_feature_status(
    tenant_id: int,
    feature_key: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    return await FeatureFlagService.get_tenant_feature_status(db, tenant_id, feature_key)




@router.put("/{key}", response_model=schemas.FeatureFlag)
async def update_flag(
    key: str,
    update_data: schemas.FeatureFlagUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    return await FeatureFlagService.update_flag(db, key, update_data)


@router.get(
    "/clinical-drift/{tenant_id}",
    response_model=schemas.TenantClinicalDriftReport,
    summary="Clinical Drift and Mapping Error Observer",
)
async def get_clinical_drift_features_alias(
    tenant_id: int,
    limit_patients: int = 500,
    after_patient_id: int = 0,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    from backend.services.clinical_drift_observer_service import ClinicalDriftObserverService
    service = ClinicalDriftObserverService(db)
    return await service.compute_tenant_drift(
        tenant_id=tenant_id,
        limit_patients=limit_patients,
        after_patient_id=after_patient_id,
    )


# Emergency Commercial Restrictions (PR-04 Task 8)
@router.get("/emergency-restrictions", response_model=StandardResponse[schemas.EmergencyRestrictionResponse])
async def get_emergency_restrictions(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    """List all platform emergency restrictions."""
    prefix = "emergency_restriction_"
    stmt = select(models.SystemSetting).where(models.SystemSetting.key.startswith(prefix))
    res = await db.execute(stmt)
    rows = res.scalars().all()
    active = [r.key[len(prefix):] for r in rows if r.value == "true"]
    return success_response(
        data=schemas.EmergencyRestrictionResponse(active_restrictions=active)
    )


@router.post("/emergency-restrictions", response_model=StandardResponse[schemas.EmergencyRestrictionResponse])
async def set_emergency_restriction(
    req: schemas.EmergencyRestrictionUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    """Set or lift an emergency capability restriction with transactional audit."""
    canon = canonicalize_capability_key(req.capability_key)
    if not canon or canon not in CAPABILITY_REGISTRY:
        raise HTTPException(
            status_code=422, detail=f"Unknown capability key '{req.capability_key}'"
        )

    setting_key = f"emergency_restriction_{canon}"
    stmt = select(models.SystemSetting).where(models.SystemSetting.key == setting_key)
    row = (await db.execute(stmt)).scalar_one_or_none()
    old_state = row.value if row else "false"
    new_state = "true" if req.is_restricted else "false"

    if row:
        row.value = new_state
    else:
        db.add(models.SystemSetting(key=setting_key, value=new_state))

    audit = models.AuditLog(
        action="EMERGENCY_RESTRICTION_UPDATE",
        entity_type="SystemSetting",
        performed_by_id=current_user.id,
        performed_by_username=current_user.username,
        old_value=old_state,
        new_value=new_state,
        details=f"Emergency restriction for '{canon}' set to {req.is_restricted}. Reason: {req.reason}",
    )
    db.add(audit)
    await db.commit()

    prefix = "emergency_restriction_"
    stmt_all = select(models.SystemSetting).where(models.SystemSetting.key.startswith(prefix))
    res_all = await db.execute(stmt_all)
    all_rows = res_all.scalars().all()
    active = [r.key[len(prefix):] for r in all_rows if r.value == "true"]

    return success_response(
        data=schemas.EmergencyRestrictionResponse(
            active_restrictions=active,
            updated_at=datetime.now(timezone.utc),
        ),
        message=f"Emergency restriction for '{canon}' updated successfully",
    )
