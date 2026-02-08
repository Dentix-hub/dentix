from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend import models, schemas
from backend.database import get_db
from backend.services.feature_service import FeatureFlagService
from backend.routers.auth import get_current_user
from backend.constants import ROLES

router = APIRouter(
    prefix="/admin/features",
    tags=["Admin Features"],
    responses={404: {"description": "Not found"}},
)

# Dependency to check for super admin (Reuse from security router or move to common)
def get_super_admin(current_user: models.User = Depends(get_current_user)):
    # Allow 'super_admin' OR 'admin' with no tenant
    if current_user.role == ROLES.SUPER_ADMIN:
        return current_user
        
    if current_user.role == ROLES.ADMIN and current_user.tenant_id is None:
        return current_user

    raise HTTPException(status_code=403, detail="Not authorized")

@router.get("/", response_model=List[schemas.FeatureFlag])
def get_all_flags(db: Session = Depends(get_db), current_user: models.User = Depends(get_super_admin)):
    return FeatureFlagService.get_all_flags(db)

@router.post("/", response_model=schemas.FeatureFlag)
def create_flag(
    flag: schemas.FeatureFlagCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_super_admin)
):
    return FeatureFlagService.create_flag(db, flag)

@router.post("/override", response_model=schemas.TenantFeature)
def set_tenant_override(
    override: schemas.TenantFeature, # We might need a simpler Create schema
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_super_admin)
):
    # override schema currently has id, tenant_id, feature_key, is_enabled
    # We should probably ignore ID for creation.
    return FeatureFlagService.set_tenant_override(
        db, 
        override.tenant_id, 
        override.feature_key, 
        override.is_enabled
    )

@router.put("/{key}", response_model=schemas.FeatureFlag)
def update_flag(
    key: str,
    update_data: dict, # Using dict for flexibility or a specific UpdateSchema
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_super_admin)
):
    return FeatureFlagService.update_flag(db, key, update_data)
