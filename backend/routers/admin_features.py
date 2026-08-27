from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
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


@router.put("/{key}", response_model=schemas.FeatureFlag)
async def update_flag(
    key: str,
    update_data: schemas.FeatureFlagUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    return await FeatureFlagService.update_flag(db, key, update_data)
