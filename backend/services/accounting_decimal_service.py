"""Decimal-safe accounting facade for Finance V2 compensation endpoints.

PostgreSQL NUMERIC values arrive as ``Decimal``.  Legacy compensation code still
mixes those values with float literals (for example ``commission / 100.0``).
This facade preserves the current business formulas while normalizing only the
legacy float calculation boundary.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from backend import models
from backend.core.money import as_decimal, quantize_money
from backend.services.accounting_service import AccountingService as BaseAccountingService


class _NumericSafeUserProxy:
    """Forward a User while exposing legacy compensation fields as floats.

    The base accounting implementation is still float-oriented.  Converting
    these three values at that compatibility boundary avoids Decimal/float
    TypeErrors without mutating the ORM object or the database representation.
    """

    def __init__(self, user: models.User):
        self._user = user

    def __getattr__(self, name):
        return getattr(self._user, name)

    @property
    def commission_percent(self) -> float:
        return float(as_decimal(self._user.commission_percent))

    @property
    def fixed_salary(self) -> float:
        return float(as_decimal(self._user.fixed_salary))

    @property
    def per_appointment_fee(self) -> float:
        return float(as_decimal(self._user.per_appointment_fee))


class DecimalSafeAccountingService(BaseAccountingService):
    async def get_relevant_users(self, roles: List[str] = None):
        users = await super().get_relevant_users(roles)
        return [_NumericSafeUserProxy(user) for user in users]

    async def get_doctor_details_data(
        self,
        doctor_id: int,
        start,
        end,
    ) -> Optional[Dict[str, Any]]:
        """Return doctor details without mixing Decimal compensation with floats."""
        doctor = (
            await self.db.execute(
                select(models.User).where(
                    models.User.id == doctor_id,
                    models.User.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not doctor:
            return None

        start_utc, end_utc = await self._normalize_utc_range(start, end)

        treatments = (
            await self.db.execute(
                select(models.Treatment, models.Patient.name)
                .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
                .where(
                    models.Treatment.doctor_id == doctor_id,
                    models.Treatment.date >= start_utc,
                    models.Treatment.date <= end_utc,
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                    models.Treatment.is_deleted == False,  # noqa: E712
                )
                .order_by(models.Treatment.date.desc())
            )
        ).all()

        lab_orders = (
            await self.db.execute(
                select(models.LabOrder, models.Patient.name)
                .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
                .where(
                    models.LabOrder.doctor_id == doctor_id,
                    models.LabOrder.order_date >= start_utc,
                    models.LabOrder.order_date <= end_utc,
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,  # noqa: E712
                )
                .order_by(models.LabOrder.order_date.desc())
            )
        ).all()

        analytics = await self.get_doctor_revenue_analytics(start, end)
        stat = next(
            (row for row in analytics if row.get("doctor_id") == doctor_id),
            None,
        )

        total_revenue = float(stat.get("revenue") or 0.0) if stat else 0.0
        total_collected = float(stat.get("collected") or 0.0) if stat else 0.0
        total_lab_cost = float(stat.get("lab_cost") or 0.0) if stat else 0.0
        commission_percent = float(as_decimal(doctor.commission_percent))
        fixed_salary = float(as_decimal(doctor.fixed_salary))
        fixed_salary_period = (
            float(stat.get("fixed_salary_period") or 0.0) if stat else 0.0
        )
        commission_base = (
            float(stat.get("commission_base") or 0.0)
            if stat
            else max(0.0, total_collected - total_lab_cost)
        )
        commission_amount = (
            float(stat.get("commission_amount") or 0.0)
            if stat
            else float(
                quantize_money(
                    as_decimal(commission_base)
                    * as_decimal(commission_percent)
                    / as_decimal(100)
                )
            )
        )
        total_due = (
            float(stat.get("total_due") or 0.0)
            if stat
            else float(quantize_money(as_decimal(commission_amount) + as_decimal(fixed_salary)))
        )

        return {
            "doctor_id": doctor.id,
            "doctor_name": doctor.username,
            "commission_percent": commission_percent,
            "fixed_salary": fixed_salary,
            "fixed_salary_period": fixed_salary_period,
            "revenue": total_revenue,
            "total_revenue": total_revenue,
            "collected": total_collected,
            "total_collected": total_collected,
            "lab_cost": total_lab_cost,
            "total_lab_cost": total_lab_cost,
            "net_revenue": (
                float(stat.get("net_revenue") or 0.0)
                if stat
                else total_revenue - total_lab_cost
            ),
            "commission_base": commission_base,
            "commission_amount": commission_amount,
            "total_due": total_due,
            "treatments": [
                {
                    "id": treatment.id,
                    "date": treatment.date,
                    "procedure": treatment.procedure,
                    "cost": treatment.cost,
                    "discount": treatment.discount,
                    "net": as_decimal(treatment.cost) - as_decimal(treatment.discount),
                    "patient_id": treatment.patient_id,
                    "patient_name": patient_name,
                }
                for treatment, patient_name in treatments
            ],
            "lab_orders": [
                {
                    "id": lab.id,
                    "date": lab.order_date,
                    "work_type": lab.work_type,
                    "cost": lab.cost,
                    "patient_id": lab.patient_id,
                    "patient_name": patient_name,
                }
                for lab, patient_name in lab_orders
            ],
        }


AccountingService = DecimalSafeAccountingService
