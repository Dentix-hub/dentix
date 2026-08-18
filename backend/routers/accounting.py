"""Accounting router facade with corrected period aggregation semantics.

The legacy router is retained verbatim in ``accounting_legacy.py``. All routes
remain registered except ``/comprehensive-stats``, which is replaced here so
its direct aggregate queries use the same tenant-time, soft-delete, and
outstanding-balance contracts as ``AccountingService``.
"""

from typing import Optional

from fastapi import Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, error_response, success_response
from backend.services.accounting_service import AccountingService
from backend.services.billing_service import BillingService

from . import accounting_legacy as _legacy
from .auth import get_async_db

router = _legacy.router

router.routes[:] = [
    route
    for route in router.routes
    if not (
        getattr(route, "path", None) == "/accounting/comprehensive-stats"
        and "GET" in getattr(route, "methods", set())
    )
]


@router.get("/comprehensive-stats", response_model=StandardResponse[dict])
async def get_comprehensive_stats(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    patient_id: Optional[int] = Query(None, description="Patient ID to filter by"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Return one reconciled financial snapshot for the requested tenant-local period."""
    service = AccountingService(db, current_user.tenant_id)
    try:
        start, end = service.parse_date_range(start_date, end_date)
        start_utc, end_utc = await service._normalize_utc_range(start, end)
    except ValueError:
        return error_response(message="Invalid date format")

    if end_utc < start_utc:
        return error_response(message="end_date must be on or after start_date", status_code=400)

    total_income = await service.get_total_income(start, end, patient_id=patient_id)
    total_collected = await service.get_total_collected(start, end, patient_id=patient_id)

    base_treatment_filters = [
        models.Treatment.tenant_id == current_user.tenant_id,
        models.Patient.tenant_id == current_user.tenant_id,
        models.Patient.is_deleted == False,
        models.Treatment.is_deleted == False,
        models.Treatment.date >= start_utc,
        models.Treatment.date <= end_utc,
    ]

    production_stmt = (
        select(
            func.coalesce(func.sum(models.Treatment.cost), 0.0),
            func.coalesce(func.sum(models.Treatment.discount), 0.0),
        )
        .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
        .where(*base_treatment_filters)
    )
    if patient_id:
        production_stmt = production_stmt.where(models.Treatment.patient_id == patient_id)
    gross_production, total_discounts = (await db.execute(production_stmt)).one()

    treatment_count_stmt = (
        select(func.count(models.Treatment.id))
        .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
        .where(*base_treatment_filters)
    )
    unique_patients_stmt = (
        select(func.count(models.Treatment.patient_id.distinct()))
        .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
        .where(*base_treatment_filters)
    )
    if patient_id:
        treatment_count_stmt = treatment_count_stmt.where(models.Treatment.patient_id == patient_id)
        unique_patients_stmt = unique_patients_stmt.where(models.Treatment.patient_id == patient_id)

    total_appointments = int((await db.execute(treatment_count_stmt)).scalar() or 0)
    unique_patients_count = int((await db.execute(unique_patients_stmt)).scalar() or 0)

    doctor_dues, total_doctor_dues = await service.calculate_doctor_dues(
        start, end, patient_id=patient_id
    )

    # A clinic-level monthly fixed salary cannot be charged to one patient's
    # statement. Patient-scoped compensation contains only commission generated
    # by that patient's period collections (plus that patient's lab impact).
    if patient_id:
        patient_doctor_dues = []
        for row in doctor_dues:
            commission_amount = float(row.get("commission_amount") or 0.0)
            row["fixed_salary_period"] = 0.0
            row["total_due"] = commission_amount
            if any(
                float(row.get(field) or 0.0) != 0.0
                for field in ("revenue", "collected", "lab_cost", "commission_amount")
            ):
                patient_doctor_dues.append(row)
        doctor_dues = patient_doctor_dues
        total_doctor_dues = round(
            sum(float(row.get("total_due") or 0.0) for row in doctor_dues), 2
        )

    if patient_id:
        staff_dues, total_staff_dues = [], 0.0
        total_expenses = 0.0
    else:
        staff_dues, total_staff_dues = await service.calculate_staff_dues(
            start, end, total_appointments
        )
        total_expenses = await service.get_total_expenses(start, end)

    total_lab_costs = await service.get_total_lab_costs(start, end, patient_id=patient_id)

    total_deductions = (
        float(total_doctor_dues)
        + float(total_staff_dues)
        + float(total_expenses)
        + float(total_lab_costs)
    )
    net_profit = float(total_collected) - total_deductions

    billing_service = BillingService(db, current_user.tenant_id)
    real_outstanding = await billing_service.get_outstanding_balance(patient_id)

    return success_response(
        data={
            "period": {"start": start_date, "end": end_date},
            "income": {
                "total_revenue": float(total_income),
                "gross_revenue": float(gross_production),
                "total_discounts": float(total_discounts),
                "net_revenue": float(total_income),
                "total_collected": float(total_collected),
                "outstanding": float(real_outstanding),
                "all_time_outstanding": float(real_outstanding),
                "period_balance": float(total_income) - float(total_collected),
                "total_appointments": total_appointments,
                "unique_patients": unique_patients_count,
            },
            "deductions": {
                "doctor_dues": {"total": float(total_doctor_dues), "details": doctor_dues},
                "staff_dues": {"total": float(total_staff_dues), "details": staff_dues},
                "lab_costs": float(total_lab_costs),
                "expenses": float(total_expenses),
                "total_deductions": total_deductions,
            },
            "net_profit": net_profit,
        },
        message="Comprehensive stats retrieved successfully",
    )


for _name in dir(_legacy):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_legacy, _name)
