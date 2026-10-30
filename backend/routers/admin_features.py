from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from backend import models, schemas
from backend.database import get_async_db
from backend.services.feature_service import FeatureFlagService
from backend.core.permissions import Role
from backend.core.permissions import Permission, require_permission


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
