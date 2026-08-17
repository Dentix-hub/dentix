"""
Dashboard Router
Handles dashboard statistics using the tenant's configured business day.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, crud
from .auth import get_async_db
from backend.services.cache_service import cached, invalidate_dashboard_cache
from backend.services.tenant_time_service import get_tenant_time_context
from backend.core.limiter import limiter
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse

router = APIRouter(prefix="/stats", tags=["Dashboard"])


def _visibility_scope(current_user: models.User) -> tuple[int | None, int | None, bool]:
    """Return patient-finance scope, appointment scope, and doctor flag.

    Financial visibility follows the established DENTIX rule based on
    Patient.assigned_doctor_id, with the existing cross-doctor-history override.
    Appointment counts remain scoped to the doctor's own appointments.
    """
    is_doctor = current_user.role == "doctor"
    can_view_all_finance = bool(
        getattr(current_user, "can_view_other_doctors_history", False)
    )
    doctor_patient_scope_id = (
        current_user.id if is_doctor and not can_view_all_finance else None
    )
    appointment_doctor_id = current_user.id if is_doctor else None
    return doctor_patient_scope_id, appointment_doctor_id, is_doctor


@router.get("/dashboard", response_model=StandardResponse[schemas.DashboardStats])
@limiter.limit("30/minute")
async def get_dashboard_stats(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.APPOINTMENT_READ)),
):
    """Get dashboard statistics for the current tenant business day."""
    context = await get_tenant_time_context(db, current_user.tenant_id)
    patient_scope_id, appointment_doctor_id, is_doctor = _visibility_scope(current_user)
    return await _get_cached_dashboard_stats(
        current_user.tenant_id,
        patient_scope_id,
        appointment_doctor_id,
        is_doctor,
        context.timezone_name,
        context.business_date.isoformat(),
        db,
    )


@cached(key_prefix="dashboard_stats", expire=120)
async def _get_cached_dashboard_stats(
    tenant_id: int,
    doctor_patient_scope_id: int | None,
    appointment_doctor_id: int | None,
    is_doctor: bool,
    timezone_name: str,
    business_date: str,
    db: AsyncSession,
):
    """Cache by tenant, visibility scope, timezone, and local business date."""
    data = await crud.get_dashboard_stats(
        db,
        tenant_id,
        timezone_name=timezone_name,
        business_date=date.fromisoformat(business_date),
        doctor_patient_scope_id=doctor_patient_scope_id,
        appointment_doctor_id=appointment_doctor_id,
        is_doctor=is_doctor,
    )
    return success_response(data=data)


@router.put("/timezone", response_model=StandardResponse[schemas.Tenant])
async def update_tenant_timezone(
    config: schemas.TenantUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update the current clinic's IANA timezone through an authorized flow."""
    if config.timezone is None:
        raise HTTPException(status_code=400, detail="timezone is required")

    tenant = (
        await db.execute(
            select(models.Tenant).where(models.Tenant.id == current_user.tenant_id)
        )
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.timezone = config.timezone
    await db.commit()
    await db.refresh(tenant)
    invalidate_dashboard_cache(tenant.id)
    return success_response(data=tenant, message="Tenant timezone updated")


@router.get("/finance", response_model=StandardResponse[schemas.FinancialStats])
@limiter.limit("30/minute")
async def get_finance_stats(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get financial statistics for the current tenant business day."""
    context = await get_tenant_time_context(db, current_user.tenant_id)
    patient_scope_id, _, is_doctor = _visibility_scope(current_user)
    return await _get_cached_finance_stats(
        current_user.tenant_id,
        patient_scope_id,
        is_doctor,
        context.timezone_name,
        context.business_date.isoformat(),
        db,
    )


@cached(key_prefix="finance_stats", expire=60)
async def _get_cached_finance_stats(
    tenant_id: int,
    doctor_patient_scope_id: int | None,
    is_doctor: bool,
    timezone_name: str,
    business_date: str,
    db: AsyncSession,
):
    """Cache finance data with tenant business date in the cache identity."""
    data = await crud.get_financial_stats(
        db,
        tenant_id,
        timezone_name=timezone_name,
        business_date=date.fromisoformat(business_date),
        doctor_patient_scope_id=doctor_patient_scope_id,
        is_doctor=is_doctor,
    )
    return success_response(data=data)
