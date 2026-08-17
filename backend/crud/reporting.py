"""Tenant-business-day reporting queries.

This module is the authoritative source for DENTIX dashboard "today" metrics.
It intentionally distinguishes UTC-by-convention event timestamps from the
legacy clinic-local appointment wall-clock field.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.utils.tenant_time import (
    serialize_utc_datetime,
    tenant_day_local_naive_bounds,
    tenant_day_utc_bounds_naive,
)


def _patient_scope(stmt, doctor_patient_scope_id: int | None):
    if doctor_patient_scope_id is not None:
        stmt = stmt.where(models.Patient.assigned_doctor_id == doctor_patient_scope_id)
    return stmt


async def get_today_debtors(
    db: AsyncSession,
    tenant_id: int,
    *,
    timezone_name: str,
    business_date: date,
    doctor_patient_scope_id: int | None = None,
) -> list[dict]:
    """Return patients with positive same-business-day treatment due.

    This calculation is shared by the dashboard card and the debtors modal.
    """
    utc_start, utc_end = tenant_day_utc_bounds_naive(
        timezone_name,
        local_date=business_date,
    )

    cost_stmt = (
        select(
            models.Treatment.patient_id,
            func.sum(models.Treatment.cost - models.Treatment.discount).label("total_cost"),
        )
        .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Treatment.date >= utc_start,
            models.Treatment.date < utc_end,
        )
        .group_by(models.Treatment.patient_id)
    )
    cost_stmt = _patient_scope(cost_stmt, doctor_patient_scope_id)
    cost_rows = (await db.execute(cost_stmt)).all()
    costs_by_pid = {
        row.patient_id: float(row.total_cost or 0.0)
        for row in cost_rows
    }

    if not costs_by_pid:
        return []

    patient_ids = list(costs_by_pid)

    paid_stmt = (
        select(
            models.Payment.patient_id,
            func.sum(models.Payment.amount).label("total_paid"),
        )
        .join(models.Patient, models.Payment.patient_id == models.Patient.id)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Payment.patient_id.in_(patient_ids),
            models.Payment.date >= utc_start,
            models.Payment.date < utc_end,
        )
        .group_by(models.Payment.patient_id)
    )
    paid_stmt = _patient_scope(paid_stmt, doctor_patient_scope_id)
    paid_rows = (await db.execute(paid_stmt)).all()
    paid_by_pid = {
        row.patient_id: float(row.total_paid or 0.0)
        for row in paid_rows
    }

    debtor_ids = [
        patient_id
        for patient_id, total_cost in costs_by_pid.items()
        if total_cost - paid_by_pid.get(patient_id, 0.0) > 0
    ]
    if not debtor_ids:
        return []

    patient_stmt = select(models.Patient).where(
        models.Patient.tenant_id == tenant_id,
        models.Patient.is_deleted == False,  # noqa: E712
        models.Patient.id.in_(debtor_ids),
    )
    patient_stmt = _patient_scope(patient_stmt, doctor_patient_scope_id)
    patients = (await db.execute(patient_stmt)).scalars().all()
    patients_by_id = {patient.id: patient for patient in patients}

    rows: list[dict] = []
    for patient_id in debtor_ids:
        patient = patients_by_id.get(patient_id)
        if patient is None:
            continue
        total_cost = costs_by_pid.get(patient_id, 0.0)
        total_paid = paid_by_pid.get(patient_id, 0.0)
        rows.append(
            {
                "id": patient.id,
                "name": patient.name,
                "phone": str(patient.phone or ""),
                "amount": total_cost - total_paid,
                "total_cost": total_cost,
                "total_paid": total_paid,
            }
        )

    rows.sort(key=lambda row: (-row["amount"], row["name"] or "", row["id"]))
    return rows


async def get_today_payments(
    db: AsyncSession,
    tenant_id: int,
    *,
    timezone_name: str,
    business_date: date,
    doctor_patient_scope_id: int | None = None,
) -> list[dict]:
    """Return payments inside the tenant business day with explicit UTC dates."""
    utc_start, utc_end = tenant_day_utc_bounds_naive(
        timezone_name,
        local_date=business_date,
    )
    stmt = (
        select(models.Payment, models.Patient.name)
        .join(models.Patient, models.Payment.patient_id == models.Patient.id)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Payment.date >= utc_start,
            models.Payment.date < utc_end,
        )
        .order_by(models.Payment.date.desc(), models.Payment.id.desc())
    )
    stmt = _patient_scope(stmt, doctor_patient_scope_id)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": payment.id,
            "amount": float(payment.amount or 0.0),
            "date": serialize_utc_datetime(payment.date),
            "patient_name": patient_name,
            "notes": payment.notes,
        }
        for payment, patient_name in rows
    ]


async def get_financial_stats(
    db: AsyncSession,
    tenant_id: int,
    *,
    timezone_name: str,
    business_date: date,
    doctor_patient_scope_id: int | None = None,
    is_doctor: bool = False,
) -> dict:
    """Return tenant/doctor financial stats using tenant-local day semantics."""
    utc_start, utc_end = tenant_day_utc_bounds_naive(
        timezone_name,
        local_date=business_date,
    )

    treatment_stmt = (
        select(
            func.sum(models.Treatment.cost).label("total_cost"),
            func.sum(models.Treatment.discount).label("total_discount"),
            func.sum(
                case(
                    (
                        and_(
                            models.Treatment.date >= utc_start,
                            models.Treatment.date < utc_end,
                        ),
                        models.Treatment.cost - models.Treatment.discount,
                    ),
                    else_=0,
                )
            ).label("today_revenue"),
        )
        .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    )
    treatment_stmt = _patient_scope(treatment_stmt, doctor_patient_scope_id)
    treatment_row = (await db.execute(treatment_stmt)).first()

    total_cost = float(treatment_row.total_cost or 0.0)
    total_discount = float(treatment_row.total_discount or 0.0)
    total_revenue = total_cost - total_discount
    today_revenue = float(treatment_row.today_revenue or 0.0)

    payment_stmt = (
        select(
            func.sum(models.Payment.amount).label("total_received"),
            func.sum(
                case(
                    (
                        and_(
                            models.Payment.date >= utc_start,
                            models.Payment.date < utc_end,
                        ),
                        models.Payment.amount,
                    ),
                    else_=0,
                )
            ).label("today_received"),
        )
        .join(models.Patient, models.Payment.patient_id == models.Patient.id)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    )
    payment_stmt = _patient_scope(payment_stmt, doctor_patient_scope_id)
    payment_row = (await db.execute(payment_stmt)).first()
    total_received = float(payment_row.total_received or 0.0)
    today_received = float(payment_row.today_received or 0.0)

    lab_stmt = (
        select(
            func.sum(models.LabOrder.cost).label("total_lab"),
            func.sum(
                case(
                    (
                        and_(
                            models.LabOrder.order_date >= utc_start,
                            models.LabOrder.order_date < utc_end,
                        ),
                        models.LabOrder.cost,
                    ),
                    else_=0,
                )
            ).label("today_lab"),
        )
        .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
        .where(
            models.LabOrder.tenant_id == tenant_id,
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    )
    lab_stmt = _patient_scope(lab_stmt, doctor_patient_scope_id)
    lab_row = (await db.execute(lab_stmt)).first()
    total_lab_costs = float(lab_row.total_lab or 0.0)
    today_lab_costs = float(lab_row.today_lab or 0.0)

    if is_doctor:
        total_expenses = 0.0
        today_expenses = 0.0
    else:
        expense_stmt = select(
            func.sum(models.Expense.cost).label("total_expenses"),
            func.sum(
                case(
                    (models.Expense.date == business_date, models.Expense.cost),
                    else_=0,
                )
            ).label("today_expenses"),
        ).where(models.Expense.tenant_id == tenant_id)
        expense_row = (await db.execute(expense_stmt)).first()
        total_expenses = float(expense_row.total_expenses or 0.0)
        today_expenses = float(expense_row.today_expenses or 0.0)

    debtors = await get_today_debtors(
        db,
        tenant_id,
        timezone_name=timezone_name,
        business_date=business_date,
        doctor_patient_scope_id=doctor_patient_scope_id,
    )
    today_outstanding = sum(float(row["amount"]) for row in debtors)

    outstanding = max(0.0, total_revenue - total_received)
    net_profit = total_received - total_expenses - total_lab_costs

    return {
        "total_revenue": total_revenue,
        "total_received": total_received,
        "outstanding": outstanding,
        "total_expenses": total_expenses + total_lab_costs,
        "net_profit": net_profit,
        "monthly_revenue": 0.0,
        "today_revenue": today_revenue,
        "today_received": today_received,
        "today_outstanding": today_outstanding,
        "today_expenses": today_expenses + today_lab_costs,
    }


async def get_dashboard_stats(
    db: AsyncSession,
    tenant_id: int,
    *,
    timezone_name: str,
    business_date: date,
    doctor_patient_scope_id: int | None = None,
    appointment_doctor_id: int | None = None,
    is_doctor: bool = False,
) -> dict:
    """Return dashboard metrics for one explicit tenant business date."""
    utc_start, utc_end = tenant_day_utc_bounds_naive(
        timezone_name,
        local_date=business_date,
    )
    local_start, local_end = tenant_day_local_naive_bounds(
        timezone_name,
        local_date=business_date,
    )

    financial = await get_financial_stats(
        db,
        tenant_id,
        timezone_name=timezone_name,
        business_date=business_date,
        doctor_patient_scope_id=doctor_patient_scope_id,
        is_doctor=is_doctor,
    )

    patient_stmt = select(func.count(models.Patient.id)).where(
        models.Patient.tenant_id == tenant_id,
        models.Patient.is_deleted == False,  # noqa: E712
    )
    patient_stmt = _patient_scope(patient_stmt, doctor_patient_scope_id)
    total_patients = int((await db.execute(patient_stmt)).scalar() or 0)

    new_patient_stmt = select(func.count(models.Patient.id)).where(
        models.Patient.tenant_id == tenant_id,
        models.Patient.is_deleted == False,  # noqa: E712
        models.Patient.created_at >= utc_start,
        models.Patient.created_at < utc_end,
    )
    new_patient_stmt = _patient_scope(new_patient_stmt, doctor_patient_scope_id)
    new_patients_today = int((await db.execute(new_patient_stmt)).scalar() or 0)

    appointment_stmt = (
        select(func.count(models.Appointment.id))
        .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
        .where(
            models.Appointment.tenant_id == tenant_id,
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Appointment.is_deleted == False,  # noqa: E712
            models.Appointment.status != "Cancelled",
            models.Appointment.date_time >= local_start,
            models.Appointment.date_time < local_end,
        )
    )
    if appointment_doctor_id is not None:
        appointment_stmt = appointment_stmt.where(
            models.Appointment.doctor_id == appointment_doctor_id
        )
    total_appointments_today = int(
        (await db.execute(appointment_stmt)).scalar() or 0
    )

    chart_dates = [business_date - timedelta(days=offset) for offset in range(6, -1, -1)]
    chart_columns = []
    for index, chart_date in enumerate(chart_dates):
        day_start, day_end = tenant_day_utc_bounds_naive(
            timezone_name,
            local_date=chart_date,
        )
        chart_columns.append(
            func.sum(
                case(
                    (
                        and_(
                            models.Payment.date >= day_start,
                            models.Payment.date < day_end,
                        ),
                        models.Payment.amount,
                    ),
                    else_=0,
                )
            ).label(f"day_{index}")
        )

    chart_stmt = (
        select(*chart_columns)
        .select_from(models.Payment)
        .join(models.Patient, models.Payment.patient_id == models.Patient.id)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    )
    chart_stmt = _patient_scope(chart_stmt, doctor_patient_scope_id)
    chart_row = (await db.execute(chart_stmt)).first()

    chart_data = [
        {
            "name": chart_date.isoformat(),
            "revenue": float(getattr(chart_row, f"day_{index}", 0.0) or 0.0),
        }
        for index, chart_date in enumerate(chart_dates)
    ]

    return {
        **financial,
        "total_patients": total_patients,
        "new_patients_today": new_patients_today,
        "total_appointments_today": total_appointments_today,
        "revenue_chart": chart_data,
        "business_date": business_date.isoformat(),
        "tenant_timezone": timezone_name,
    }
