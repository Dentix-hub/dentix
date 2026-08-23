"""Final Accounting router with Finance V2 truth and granular RBAC guards."""

from typing import Optional

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend import schemas
from backend.core.money import NonNegativeMoney, Percentage
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, error_response, success_response
from backend.schemas.finance import CompensationSettingsPatch
from backend.services.finance_summary_service import (
    CompensationSettingsService,
    FinanceSummaryService,
)

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
    ("/accounting/staff-compensation/{user_id}", "PUT"),
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
    """Patient receivables with an all-time aggregate independent of activity range/page."""
    response = await _previous._legacy.get_patients_report(
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

    data = response.get("data") if isinstance(response, dict) else None
    if isinstance(data, dict):
        truth = FinanceSummaryService(db, current_user.tenant_id)
        current_debt = await truth.get_current_patient_debt(
            patient_id=patient_id,
            search=search,
        )
        summary = data.setdefault("summary", {})
        summary["total_outstanding"] = float(current_debt)
        summary["total_outstanding_scope"] = "all_time_as_of_now"
    return response


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


async def _apply_compensation_patch(
    *,
    user_id: int,
    updates: dict,
    db: AsyncSession,
    current_user: schemas.User,
):
    service = CompensationSettingsService(db, current_user.tenant_id)
    try:
        result = await service.patch_settings(user_id, current_user, updates)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    if result is None:
        return error_response(message="User not found", status_code=404)
    return success_response(data=result, message="Compensation updated atomically")


@router.patch("/staff-compensation/{user_id}", response_model=StandardResponse[dict])
async def patch_staff_compensation(
    user_id: int,
    payload: CompensationSettingsPatch,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Canonical partial update; omitted compensation fields are preserved."""
    return await _apply_compensation_patch(
        user_id=user_id,
        updates=payload.model_dump(exclude_unset=True),
        db=db,
        current_user=current_user,
    )


@router.put("/staff-compensation/{user_id}", response_model=StandardResponse[dict])
async def update_staff_compensation_compat(
    user_id: int,
    commission_percent: Optional[Percentage] = Query(None),
    fixed_salary: Optional[NonNegativeMoney] = Query(None),
    per_appointment_fee: Optional[NonNegativeMoney] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Compatibility PUT using the same preserve-omitted-fields transaction."""
    updates = {
        key: value
        for key, value in {
            "commission_percent": commission_percent,
            "fixed_salary": fixed_salary,
            "per_appointment_fee": per_appointment_fee,
        }.items()
        if value is not None
    }
    return await _apply_compensation_patch(
        user_id=user_id,
        updates=updates,
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
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD); defaults to tenant-local current month"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD); defaults to tenant-local current month"),
    patient_id: Optional[int] = Query(None, description="Patient ID to filter by"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_READ)),
):
    """Return contract-defined Finance summary from one authoritative service."""
    service = FinanceSummaryService(db, current_user.tenant_id)
    try:
        data = await service.get_summary(
            start_date=start_date,
            end_date=end_date,
            patient_id=patient_id,
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(
        data=data,
        message="Comprehensive stats retrieved successfully",
    )


for _name in dir(_previous):
    if _name.startswith("_") or _name in globals():
        continue
    globals()[_name] = getattr(_previous, _name)
