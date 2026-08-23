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


def _remove_route(path: str, method: str) -> None:
    """Remove an inherited legacy route before registering its hardened facade."""
    router.routes[:] = [
        route
        for route in router.routes
        if not (
            getattr(route, "path", None) == path
            and method in getattr(route, "methods", set())
        )
    ]


for _path, _method in (
    ("/accounting/comprehensive-stats", "GET"),
    ("/accounting/patients-report", "GET"),
    ("/accounting/patient-report-details/{patient_id}", "GET"),
    ("/accounting/doctor-revenue", "GET"),
    ("/accounting/doctor-details/{doctor_id}", "GET"),
    ("/accounting/staff-revenue", "GET"),
    ("/accounting/salaries", "GET"),
    ("/accounting/salaries", "POST"),
    ("/accounting/salaries/{payment_id}", "DELETE"),
    ("/accounting/activity", "GET"),
):
    _remove_route(_path, _method)


@router.get("/patients-report", response_model=StandardResponse[dict])
async def get_patients_report(
    search: Optional[str] = Query(None, description="Search by patient name or phone"),
    patient_id: Optional[int] = Query(None, description="Filter by specific patient ID"),
    outstanding_only: bool = Query(False, description="Filter only patients with a positive balance in the selected period"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.RECEIVABLE_READ)),
):
    """Patient receivables remain available to collection-authorized staff only."""
    return await _previous._legacy.get_patients_report(
        search=search,
        patient_id=patient_id,
        outstanding_only=outstanding_only,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
        db=db,
        current_user=current_user,
    )


@router.get("/patient-report-details/{patient_id}", response_model=StandardResponse[dict])
async def get_patient_report_details(
    patient_id: int,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.RECEIVABLE_READ)),
):
    """Expose only the patient-level financial drill-down to collection roles."""
    return await _previous._legacy.get_patient_report_details(
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
    )


@router.get("/doctor-revenue", response_model=StandardResponse[dict])
async def get_doctor_revenue(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.COMPENSATION_READ)),
):
    return await _previous._legacy.get_doctor_revenue(
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
    )


@router.get("/doctor-details/{doctor_id}", response_model=StandardResponse[dict])
async def get_doctor_details(
    doctor_id: int,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.COMPENSATION_READ)),
):
    return await _previous._legacy.get_doctor_details(
        doctor_id=doctor_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
    )


@router.get("/staff-revenue", response_model=StandardResponse[dict])
async def get_staff_revenue(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.COMPENSATION_READ)),
):
    return await _previous._legacy.get_staff_revenue(
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
    )


@router.get("/salaries", response_model=StandardResponse[dict])
async def get_salaries_status(
    month: str = Query(..., description="Month in format YYYY-MM"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PAYROLL_READ)),
):
    return await _previous._legacy.get_salaries_status(
        month=month,
        db=db,
        current_user=current_user,
    )


@router.post("/salaries", response_model=StandardResponse[dict])
async def record_salary_payment(
    user_id: int,
    month: str = Query(..., description="Month in format YYYY-MM"),
    amount: float = 0.0,
    is_partial: bool = False,
    days_worked: Optional[int] = None,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PAYROLL_MANAGE)),
):
    return await _previous._legacy.record_salary_payment(
        user_id=user_id,
        month=month,
        amount=amount,
        is_partial=is_partial,
        days_worked=days_worked,
        notes=notes,
        db=db,
        current_user=current_user,
    )


@router.delete("/salaries/{payment_id}", response_model=StandardResponse[dict])
async def delete_salary_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PAYROLL_MANAGE)),
):
    return await _previous._legacy.delete_salary_payment(
        payment_id=payment_id,
        db=db,
        current_user=current_user,
    )


@router.get("/activity", response_model=StandardResponse[dict])
async def get_financial_activity(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    types: Optional[str] = Query(None, description="Comma-separated event types (payment,expense,lab,salary)"),
    search: Optional[str] = Query(None, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_READ)),
):
    return await _previous._legacy.get_financial_activity(
        start_date=start_date,
        end_date=end_date,
        types=types,
        search=search,
        skip=skip,
        limit=limit,
        db=db,
        current_user=current_user,
    )


@router.get("/comprehensive-stats", response_model=StandardResponse[dict])
async def get_comprehensive_stats(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    patient_id: Optional[int] = Query(None, description="Patient ID to filter by"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_READ)),
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
