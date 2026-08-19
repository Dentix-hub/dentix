"""Corrected financial reporting facade.

The dashboard/reporting API remains unchanged. Treatment-derived totals exclude
soft-deleted rows while event ownership continues to follow the tenant-owned
Patient relationship so historical NULL event tenant IDs remain visible only
to their owning clinic.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.crud import reporting_legacy as _legacy
from backend.utils.tenant_time import tenant_day_utc_bounds_naive


async def get_today_debtors(
    db: AsyncSession,
    tenant_id: int,
    *,
    timezone_name: str,
    business_date: date,
    doctor_patient_scope_id: int | None = None,
) -> list[dict]:
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
            models.Treatment.is_deleted == False,  # noqa: E712
            models.Treatment.date >= utc_start,
            models.Treatment.date < utc_end,
        )
        .group_by(models.Treatment.patient_id)
    )
    cost_stmt = _legacy._patient_scope(cost_stmt, doctor_patient_scope_id)
    cost_rows = (await db.execute(cost_stmt)).all()
    costs = {row.patient_id: float(row.total_cost or 0.0) for row in cost_rows}
    if not costs:
        return []

    paid_stmt = (
        select(
            models.Payment.patient_id,
            func.sum(models.Payment.amount).label("total_paid"),
        )
        .join(models.Patient, models.Payment.patient_id == models.Patient.id)
        .where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,  # noqa: E712
            models.Payment.patient_id.in_(list(costs)),
            models.Payment.date >= utc_start,
            models.Payment.date < utc_end,
        )
        .group_by(models.Payment.patient_id)
    )
    paid_stmt = _legacy._patient_scope(paid_stmt, doctor_patient_scope_id)
    paid_rows = (await db.execute(paid_stmt)).all()
    paid = {row.patient_id: float(row.total_paid or 0.0) for row in paid_rows}

    debtor_ids = [
        patient_id
        for patient_id, total_cost in costs.items()
        if total_cost - paid.get(patient_id, 0.0) > 0
    ]
    if not debtor_ids:
        return []

    patient_stmt = select(models.Patient).where(
        models.Patient.tenant_id == tenant_id,
        models.Patient.is_deleted == False,  # noqa: E712
        models.Patient.id.in_(debtor_ids),
    )
    patient_stmt = _legacy._patient_scope(patient_stmt, doctor_patient_scope_id)
    patients = {
        patient.id: patient
        for patient in (await db.execute(patient_stmt)).scalars().all()
    }

    rows = []
    for patient_id in debtor_ids:
        patient = patients.get(patient_id)
        if patient is None:
            continue
        total_cost = costs[patient_id]
        total_paid = paid.get(patient_id, 0.0)
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


async def get_financial_stats(
    db: AsyncSession,
    tenant_id: int,
    *,
    timezone_name: str,
    business_date: date,
    doctor_patient_scope_id: int | None = None,
    is_doctor: bool = False,
) -> dict:
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
            models.Treatment.is_deleted == False,  # noqa: E712
        )
    )
    treatment_stmt = _legacy._patient_scope(treatment_stmt, doctor_patient_scope_id)
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
    payment_stmt = _legacy._patient_scope(payment_stmt, doctor_patient_scope_id)
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
    lab_stmt = _legacy._patient_scope(lab_stmt, doctor_patient_scope_id)
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


# Patch the legacy module globals so its unchanged dashboard composition calls
# the corrected financial functions defined above.
_legacy.get_today_debtors = get_today_debtors
_legacy.get_financial_stats = get_financial_stats
get_today_payments = _legacy.get_today_payments
get_dashboard_stats = _legacy.get_dashboard_stats
