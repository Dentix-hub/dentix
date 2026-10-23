"""
Super-Admin Finance Parity Router (G14-M06, G14-M07, G14-M08).

Strictly read-only endpoints providing legacy vs shadow VNext financial parity
observability for super-admins across patients and clinics.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.database import get_async_db
from backend.routers.admin_features import get_super_admin
from backend.services.finance_parity_service import FinanceParityService

router = APIRouter(
    prefix="/admin/finance-parity",
    tags=["Admin Finance Parity"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/{tenant_id}",
    response_model=schemas.TenantFinanceParityReport,
    summary="Tenant-level financial parity report",
)
async def get_tenant_finance_parity(
    tenant_id: int,
    limit_patients: int = Query(100, ge=1, le=1000, description="Max patients to evaluate"),
    after_patient_id: int = Query(0, ge=0, description="Pagination cursor for patient_id"),
    discrepancies_only: bool = Query(False, description="Filter only patients with financial drift"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    """
    Compute tenant-aggregated financial parity metrics (G14-M08).
    Super-admin only. Strictly read-only (zero database writes).
    """
    service = FinanceParityService(db)
    return await service.compute_tenant_parity(
        tenant_id=tenant_id,
        limit_patients=limit_patients,
        after_patient_id=after_patient_id,
        discrepancies_only=discrepancies_only,
    )


@router.get(
    "/{tenant_id}/patients/{patient_id}",
    response_model=schemas.PatientFinanceParityDetail,
    summary="Patient-level financial parity report",
)
async def get_patient_finance_parity(
    tenant_id: int,
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    """
    Compute single-patient financial parity breakdown (G14-M07).
    Super-admin only. Strictly read-only (zero database writes).
    """
    service = FinanceParityService(db)
    return await service.compute_patient_parity(
        tenant_id=tenant_id,
        patient_id=patient_id,
    )


@router.get(
    "/{tenant_id}/lab-anomalies",
    response_model=schemas.TenantLabAnomalyReport,
    summary="Tenant-level legacy lab double-charge anomalies report",
)
async def get_tenant_lab_anomalies(
    tenant_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Max anomalies to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    patient_id: int | None = Query(None, description="Optional filter by patient_id"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_super_admin),
):
    """
    Detect legacy lab double-charge cases and produce deterministic remediation report (G14-M09, G14-M10).
    Super-admin only. Strictly read-only (zero database writes).
    """
    service = FinanceParityService(db)
    return await service.detect_lab_double_charge_anomalies(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        patient_id=patient_id,
    )

