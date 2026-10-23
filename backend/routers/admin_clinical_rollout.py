"""
Admin Clinical Rollout Router (G16-M01, G16-M02, G16-M08, G16-M10).

Super-admin endpoints for managing tenant-level clinical rollout modes,
read-only VNext enforcement, and instant atomic rollback.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.database import get_async_db
from backend.routers.admin_features import get_super_admin
from backend.services.clinical_rollout_service import ClinicalRolloutService

router = APIRouter(
    prefix="/admin/clinical-rollout",
    tags=["Admin Clinical Rollout"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/{tenant_id}/status",
    response_model=schemas.TenantClinicalRolloutStatus,
    summary="Get tenant clinical rollout status",
)
async def get_tenant_clinical_rollout_status(
    tenant_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    """
    Get current clinical rollout mode and flag states for a tenant (G16-M01, G16-M02).
    Super-admin only. Strictly read-only (zero database writes).
    """
    service = ClinicalRolloutService(db)
    return await service.get_rollout_status(tenant_id)


@router.post(
    "/{tenant_id}/rollback",
    response_model=schemas.TenantClinicalRolloutResponse,
    summary="Atomically rollback tenant to LEGACY_ONLY mode",
)
async def rollback_tenant_clinical_rollout(
    tenant_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    """
    Atomically rollback a tenant to LEGACY_ONLY mode (G16-M08).
    Disables clinical_vnext_native_writes, clinical_vnext_primary,
    clinical_vnext_shadow, and clinical_vnext_finance_read in a single transaction.
    Audited with log_admin_action. Super-admin only.
    """
    service = ClinicalRolloutService(db)
    return await service.rollback_tenant(tenant_id, admin_user=current_user)


@router.post(
    "/{tenant_id}/mode",
    response_model=schemas.TenantClinicalRolloutResponse,
    summary="Set tenant clinical rollout mode atomically",
)
async def set_tenant_clinical_rollout_mode(
    tenant_id: int,
    payload: schemas.TenantClinicalRolloutModeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    """
    Set tenant clinical rollout mode atomically (G16-M01, G16-M02, G16-M08).
    Modes:
    - LEGACY_ONLY: pure legacy behavior, native writes disabled
    - SHADOW: legacy authoritative, native shadow sync active
    - VNEXT_PRIMARY_READ_ONLY: VNext chart active, native writes disabled (fail-closed 404)
    - VNEXT_PRIMARY_READ_WRITE: VNext primary active, native writes enabled
    Audited with log_admin_action. Super-admin only.
    """
    service = ClinicalRolloutService(db)
    return await service.set_tenant_rollout_mode(
        tenant_id=tenant_id,
        target_mode=payload.mode,
        admin_user=current_user,
    )
