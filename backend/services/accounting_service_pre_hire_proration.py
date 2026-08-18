"""Final Finance V2 accounting facade.

Builds on the period/timezone correctness layer while preserving historical
rows whose event-level ``tenant_id`` can be NULL. Tenant isolation for those
legacy rows is enforced through their tenant-owned Patient relationship, which
is the established DENTIX compatibility contract.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select

from backend import models
from backend.core.permissions import DOCTOR_ROLES
from backend.services.accounting_service_legacy import AccountingService as LegacyAccountingService
from backend.services.accounting_service_period import AccountingService as PeriodAccountingService


class AccountingService(PeriodAccountingService):
    """Finance correctness with tenant-safe legacy-row compatibility."""

    async def get_treatment_stats_by_doctor(
        self,
        start,
        end,
        doctor_ids: List[int],
        patient_id: Optional[int] = None,
    ) -> Dict[int, Dict[str, Any]]:
        start, end = await self._normalize_utc_range(start, end)
        stmt = (
            select(
                models.Treatment.doctor_id,
                func.count(models.Treatment.id).label("treatment_count"),
                func.sum(models.Treatment.cost).label("gross_cost"),
                func.sum(models.Treatment.discount).label("total_discount"),
                func.sum(models.Treatment.cost - models.Treatment.discount).label("revenue"),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
        )
        if doctor_ids:
            stmt = stmt.where(models.Treatment.doctor_id.in_(doctor_ids))
        if patient_id:
            stmt = stmt.where(models.Treatment.patient_id == patient_id)
        rows = (await self.db.execute(stmt.group_by(models.Treatment.doctor_id))).all()
        return {
            row.doctor_id: {
                "treatment_count": int(row.treatment_count or 0),
                "gross_cost": float(row.gross_cost or 0.0),
                "total_discount": float(row.total_discount or 0.0),
                "revenue": float(row.revenue or 0.0),
            }
            for row in rows
        }

    async def get_total_income(self, start, end, patient_id: Optional[int] = None) -> float:
        start, end = await self._normalize_utc_range(start, end)
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
        )
        if patient_id:
            stmt = stmt.where(models.Treatment.patient_id == patient_id)
        return float((await self.db.execute(stmt)).scalar() or 0.0)

    async def get_total_collected(self, start, end, patient_id: Optional[int] = None) -> float:
        start, end = await self._normalize_utc_range(start, end)
        stmt = (
            select(func.sum(models.Payment.amount))
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= start,
                models.Payment.date <= end,
            )
        )
        if patient_id:
            stmt = stmt.where(models.Payment.patient_id == patient_id)
        return float((await self.db.execute(stmt)).scalar() or 0.0)

    async def get_doctor_revenue_analytics(
        self, start, end, patient_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Attribute every period payment exactly once to actual providers."""
        original_start, original_end = start, end
        start, end = await self._normalize_utc_range(start, end)
        users = await self.get_relevant_users(DOCTOR_ROLES + ["admin", "super_admin"])
        user_ids = [user.id for user in users]

        stats_map = await self.get_treatment_stats_by_doctor(
            start, end, user_ids, patient_id
        )
        lab_map = await self.get_lab_costs_by_doctor(
            start, end, user_ids, patient_id
        )

        # All-time active net production is the allocation basis for a payment
        # received today for work that may have been performed earlier.
        allocation_stmt = (
            select(
                models.Treatment.doctor_id,
                models.Treatment.patient_id,
                func.sum(models.Treatment.cost - models.Treatment.discount).label("net"),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
                models.Treatment.doctor_id.in_(user_ids),
            )
        )
        if patient_id:
            allocation_stmt = allocation_stmt.where(
                models.Treatment.patient_id == patient_id
            )
        allocation_rows = (
            await self.db.execute(
                allocation_stmt.group_by(
                    models.Treatment.doctor_id,
                    models.Treatment.patient_id,
                )
            )
        ).all()

        doctor_patient_net: Dict[int, Dict[int, float]] = defaultdict(dict)
        patient_total_net: Dict[int, float] = defaultdict(float)
        for doctor_id, pat_id, net in allocation_rows:
            value = max(0.0, float(net or 0.0))
            doctor_patient_net[doctor_id][pat_id] = value
            patient_total_net[pat_id] += value

        payment_stmt = (
            select(
                models.Payment.doctor_id,
                models.Payment.patient_id,
                models.Payment.amount,
            )
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= start,
                models.Payment.date <= end,
            )
        )
        if patient_id:
            payment_stmt = payment_stmt.where(models.Payment.patient_id == patient_id)
        payments = (await self.db.execute(payment_stmt)).all()

        direct: Dict[int, float] = defaultdict(float)
        unassigned: Dict[int, float] = defaultdict(float)
        for doctor_id, pat_id, amount in payments:
            value = float(amount or 0.0)
            reliable_direct_attribution = (
                doctor_id in user_ids
                and doctor_patient_net.get(doctor_id, {}).get(pat_id, 0.0) > 0
            )
            if reliable_direct_attribution:
                direct[doctor_id] += value
            else:
                unassigned[pat_id] += value

        allocated: Dict[int, float] = defaultdict(float)
        for pat_id, amount in unassigned.items():
            denominator = patient_total_net.get(pat_id, 0.0)
            if denominator <= 0:
                continue
            for doctor_id in user_ids:
                basis = doctor_patient_net.get(doctor_id, {}).get(pat_id, 0.0)
                if basis > 0:
                    allocated[doctor_id] += amount * (basis / denominator)

        result: List[Dict[str, Any]] = []
        for user in users:
            doctor_id = user.id
            stats = stats_map.get(
                doctor_id,
                {
                    "treatment_count": 0,
                    "gross_cost": 0.0,
                    "total_discount": 0.0,
                    "revenue": 0.0,
                },
            )
            lab_cost = float(lab_map.get(doctor_id, 0.0))
            collected = round(
                direct.get(doctor_id, 0.0) + allocated.get(doctor_id, 0.0),
                2,
            )
            commission_percent = float(user.commission_percent or 0.0)
            monthly_fixed = float(user.fixed_salary or 0.0)
            fixed_period = await self._period_fixed_amount(
                monthly_fixed,
                original_start,
                original_end,
            )
            commission_base = max(0.0, collected - lab_cost)
            commission_amount = round(
                commission_base * (commission_percent / 100.0),
                2,
            )
            result.append(
                {
                    "doctor_id": doctor_id,
                    "doctor_name": user.username,
                    "treatments": stats["treatment_count"],
                    "gross_cost": stats["gross_cost"],
                    "patient_discount": stats["total_discount"],
                    "revenue": stats["revenue"],
                    "collected": collected,
                    "lab_cost": lab_cost,
                    "net_revenue": stats["revenue"] - lab_cost,
                    "commission_base": commission_base,
                    "commission_percent": commission_percent,
                    "commission_amount": commission_amount,
                    "fixed_salary": monthly_fixed,
                    "fixed_salary_period": fixed_period,
                    "total_due": round(commission_amount + fixed_period, 2),
                }
            )
        return result

    async def get_doctor_details_data(self, doctor_id: int, start, end) -> Dict[str, Any]:
        start_utc, end_utc = await self._normalize_utc_range(start, end)
        data = await super().get_doctor_details_data(doctor_id, start, end)
        if not data:
            return data

        # Restore legacy NULL-event compatibility while keeping soft-delete rules.
        stmt = (
            select(models.Treatment, models.Patient.name)
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Treatment.doctor_id == doctor_id,
                models.Treatment.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start_utc,
                models.Treatment.date <= end_utc,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            .order_by(models.Treatment.date.desc())
        )
        treatments = (await self.db.execute(stmt)).all()
        data["treatments"] = [
            {
                "id": treatment.id,
                "date": treatment.date,
                "procedure": treatment.procedure,
                "cost": treatment.cost,
                "discount": treatment.discount,
                "net": treatment.cost - treatment.discount,
                "patient_id": treatment.patient_id,
                "patient_name": patient_name,
            }
            for treatment, patient_name in treatments
        ]
        return data

    async def get_patients_report(
        self,
        patient_id: Optional[int] = None,
        search: Optional[str] = None,
        outstanding_only: bool = False,
        start=None,
        end=None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        if start and end:
            normalized_start, normalized_end = await self._normalize_utc_range(start, end)
            if not patient_id and not outstanding_only:
                activity = (
                    select(models.Patient.id)
                    .where(
                        models.Patient.tenant_id == self.tenant_id,
                        models.Patient.is_deleted == False,  # noqa: E712
                        or_(
                            models.Patient.id.in_(
                                select(models.Treatment.patient_id).where(
                                    models.Treatment.is_deleted == False,  # noqa: E712
                                    models.Treatment.date >= normalized_start,
                                    models.Treatment.date <= normalized_end,
                                )
                            ),
                            models.Patient.id.in_(
                                select(models.Payment.patient_id).where(
                                    models.Payment.date >= normalized_start,
                                    models.Payment.date <= normalized_end,
                                )
                            ),
                        ),
                    )
                    .limit(1)
                )
                if (await self.db.execute(activity)).scalar_one_or_none() is None:
                    return {
                        "total": 0,
                        "summary": {
                            "total_invoiced": 0.0,
                            "total_paid": 0.0,
                            "period_balance": 0.0,
                            "total_outstanding": 0.0,
                        },
                        "patients": [],
                    }
            start, end = normalized_start, normalized_end

        # Call the original report directly so its Patient-owned tenant scope
        # remains authoritative for historical NULL event tenant IDs.
        return await LegacyAccountingService.get_patients_report(
            self,
            patient_id=patient_id,
            search=search,
            outstanding_only=outstanding_only,
            start=start,
            end=end,
            skip=skip,
            limit=limit,
        )
