"""Final Accounting router with cancelled-appointment compensation guard."""

from datetime import datetime, time, timedelta
from typing import Optional

from fastapi import Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse
from backend.services.accounting_service import AccountingService

from . import accounting_pre_cancelled_filter as _previous
from .auth import get_async_db

router = _previous.router
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
    """Return reconciled stats; cancelled appointments never earn staff visit fees."""
    response = await _previous.get_comprehensive_stats(
        start_date=start_date,
        end_date=end_date,
        patient_id=patient_id,
        db=db,
        current_user=current_user,
    )
    data = response.get("data") if isinstance(response, dict) else None
    if not data:
        return response

    service = AccountingService(db, current_user.tenant_id)
    try:
        start, end = service.parse_date_range(start_date, end_date)
        local_start_date, local_end_date = await service._local_dates_for_range(
            start,
            end,
        )
    except ValueError:
        return response

    appointment_start = datetime.combine(local_start_date, time.min)
    appointment_end = datetime.combine(
        local_end_date + timedelta(days=1),
        time.min,
    )
    appointment_stmt = (
        select(func.count(models.Appointment.id))
        .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
        .where(
            models.Patient.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Appointment.is_deleted == False,  # noqa: E712
            models.Appointment.status != "Cancelled",
            models.Appointment.date_time >= appointment_start,
            models.Appointment.date_time < appointment_end,
        )
    )
    if patient_id:
        appointment_stmt = appointment_stmt.where(
            models.Appointment.patient_id == patient_id
        )
    valid_appointments = int((await db.execute(appointment_stmt)).scalar() or 0)
    data.setdefault("income", {})["total_appointments"] = valid_appointments

    if not patient_id:
        staff_dues, total_staff_dues = await service.calculate_staff_dues(
            start,
            end,
            valid_appointments,
        )
        deductions = data.setdefault("deductions", {})
        deductions["staff_dues"] = {
            "total": float(total_staff_dues),
            "details": staff_dues,
        }
        total_deductions = (
            float(deductions.get("doctor_dues", {}).get("total") or 0.0)
            + float(total_staff_dues)
            + float(deductions.get("expenses") or 0.0)
            + float(deductions.get("lab_costs") or 0.0)
        )
        deductions["total_deductions"] = total_deductions
        data["net_profit"] = (
            float(data.get("income", {}).get("total_collected") or 0.0)
            - total_deductions
        )

    return response


for _name in dir(_previous):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_previous, _name)
