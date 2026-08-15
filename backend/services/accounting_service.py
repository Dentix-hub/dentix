"""
Accounting Service for Smart Clinic Management System.

Handles all doctor revenue, compensation, and salary calculations.
Extracted from routers/accounting.py to follow service layer pattern.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, case
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend import models
from backend.core.permissions import Role, DOCTOR_ROLES
from backend.utils.audit_logger import log_admin_action


class AccountingService:
    """Service for accounting and revenue calculations."""

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def parse_date_range(
        self, start_date: str, end_date: str
    ) -> tuple[datetime, datetime]:
        """Parse and validate date range strings."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
        return start, end

    async def get_relevant_users(self, roles: List[str] = None) -> List[models.User]:
        """Get all users with specified roles for the tenant."""
        if roles is None:
            roles = DOCTOR_ROLES
        stmt = select(models.User).where(
            models.User.tenant_id == self.tenant_id,
            models.User.role.in_(roles)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_treatment_stats_by_doctor(
        self, start: datetime, end: datetime, doctor_ids: List[int], patient_id: Optional[int] = None
    ) -> Dict[int, Dict[str, Any]]:
        """Get treatment statistics grouped by doctor."""
        stmt = (
            select(
                models.Treatment.doctor_id,
                func.count(models.Treatment.id).label("treatment_count"),
                func.sum(models.Treatment.cost).label("gross_cost"),
                func.sum(models.Treatment.discount).label("total_discount"),
                func.sum(models.Treatment.cost - models.Treatment.discount).label(
                    "revenue"
                ),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
        )
        if doctor_ids:
            stmt = stmt.where(models.Treatment.doctor_id.in_(doctor_ids))
        if patient_id:
            stmt = stmt.where(models.Treatment.patient_id == patient_id)
        stmt = stmt.group_by(models.Treatment.doctor_id)

        results = (await self.db.execute(stmt)).all()

        return {
            r.doctor_id: {
                "treatment_count": r.treatment_count,
                "gross_cost": float(r.gross_cost or 0),
                "total_discount": float(r.total_discount or 0),
                "revenue": float(r.revenue or 0),
            }
            for r in results
        }

    async def get_lab_costs_by_doctor(
        self, start: datetime, end: datetime, doctor_ids: List[int], patient_id: Optional[int] = None
    ) -> Dict[int, float]:
        """Get lab costs grouped by doctor."""
        stmt = (
            select(
                models.LabOrder.doctor_id,
                func.sum(models.LabOrder.cost).label("lab_cost"),
            )
            .where(
                models.LabOrder.tenant_id == self.tenant_id,
                models.LabOrder.order_date >= start,
                models.LabOrder.order_date <= end,
            )
        )
        if doctor_ids:
            stmt = stmt.where(models.LabOrder.doctor_id.in_(doctor_ids))
        if patient_id:
            stmt = stmt.where(models.LabOrder.patient_id == patient_id)
        stmt = stmt.group_by(models.LabOrder.doctor_id)

        results = (await self.db.execute(stmt)).all()

        return {r[0]: float(r[1] or 0) for r in results}

    async def get_total_income(self, start: datetime, end: datetime, patient_id: Optional[int] = None) -> float:
        """Calculate total income from treatments in date range."""
        stmt = (
            select(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
        )
        if patient_id:
            stmt = stmt.where(models.Treatment.patient_id == patient_id)
        res = await self.db.execute(stmt)
        return float(res.scalar() or 0.0)

    async def get_total_collected(self, start: datetime, end: datetime, patient_id: Optional[int] = None) -> float:
        """Calculate total collected payments in date range."""
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
        res = await self.db.execute(stmt)
        return float(res.scalar() or 0.0)

    async def get_total_expenses(self, start: datetime, end: datetime) -> float:
        """Calculate total expenses in date range."""
        stmt = (
            select(func.sum(models.Expense.cost))
            .where(
                models.Expense.tenant_id == self.tenant_id,
                models.Expense.date >= start.date(),
                models.Expense.date <= end.date(),
            )
        )
        res = await self.db.execute(stmt)
        return float(res.scalar() or 0.0)

    async def get_total_lab_costs(self, start: datetime, end: datetime, patient_id: Optional[int] = None) -> float:
        """Calculate total lab costs in date range."""
        stmt = (
            select(func.sum(models.LabOrder.cost))
            .where(
                models.LabOrder.tenant_id == self.tenant_id,
                models.LabOrder.order_date >= start,
                models.LabOrder.order_date <= end,
            )
        )
        if patient_id:
            stmt = stmt.where(models.LabOrder.patient_id == patient_id)
        res = await self.db.execute(stmt)
        return float(res.scalar() or 0.0)

    async def calculate_doctor_dues(
        self, start: datetime, end: datetime, patient_id: Optional[int] = None
    ) -> tuple[List[Dict[str, Any]], float]:
        """Calculate dues for all doctors in date range using COLLECTED amount."""
        # Use existing analytics to get accurate 'collected' amount
        doctors_analytics = await self.get_doctor_revenue_analytics(start, end, patient_id=patient_id)

        doctor_dues = []
        total_dues = 0.0

        for doc_stat in doctors_analytics:
            # Formula: (Collected - Lab Cost) * Commission% + Salary
            # Note: doc_stat['collected'] implies actual cash collected
            # Note: doc_stat['lab_cost'] is total lab cost

            collected = doc_stat["collected"]
            lab_cost = doc_stat["lab_cost"]

            # Base for commission is Collected - Lab Cost
            # Ensure we don't pay commission on negative if lab cost > collected?
            # Usually strict formula is (Collected - Lab), if negative, it reduces total due.
            commission_base = collected - lab_cost

            commission_percent = doc_stat["commission_percent"]
            fixed_salary = doc_stat["fixed_salary"]

            commission_amount = commission_base * (commission_percent / 100)
            total_due = commission_amount + fixed_salary

            doctor_dues.append(
                {
                    "id": doc_stat["doctor_id"],
                    "name": doc_stat["doctor_name"],
                    "revenue": doc_stat["revenue"],  # Keeping revenue for reference
                    "collected": collected,
                    "lab_cost": lab_cost,
                    "net_revenue": doc_stat[
                        "net_revenue"
                    ],  # Still useful to show potential
                    "commission_base": commission_base,  # New field for transparency
                    "commission_percent": commission_percent,
                    "commission_amount": commission_amount,
                    "fixed_salary": fixed_salary,
                    "total_due": total_due,
                }
            )
            total_dues += total_due

        return doctor_dues, total_dues

    async def get_doctor_revenue_analytics(
        self, start: datetime, end: datetime, patient_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get detailed revenue generated by each doctor, including:
        - Treatment counts/costs
        - Lab costs
        - Collected payments (with ratio calculation fallback)
        - Net revenue
        """
        # 1. Get ALL relevant users (Doctors + Admins)
        relevant_users = await self.get_relevant_users(
            DOCTOR_ROLES + ["admin", "super_admin"]
        )
        relevant_user_ids = [u.id for u in relevant_users]

        # 2. Main Stats Query
        stats_map = await self.get_treatment_stats_by_doctor(start, end, relevant_user_ids, patient_id=patient_id)

        # 3. Lab Costs
        lab_cost_map = await self.get_lab_costs_by_doctor(start, end, relevant_user_ids, patient_id=patient_id)

        # 4. Treatment Costs per Patient (for ratio calculation)
        stmt = (
            select(
                models.Treatment.doctor_id,
                models.Treatment.patient_id,
                func.sum(models.Treatment.cost).label("cost"),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
        )
        if relevant_user_ids:
            stmt = stmt.where(models.Treatment.doctor_id.in_(relevant_user_ids))
        if patient_id:
            stmt = stmt.where(models.Treatment.patient_id == patient_id)
        stmt = stmt.group_by(models.Treatment.doctor_id, models.Treatment.patient_id)
        treatment_costs = (await self.db.execute(stmt)).all()

        doctor_patient_costs = {}
        patient_total_costs = {}
        for doc_id, pat_id, cost in treatment_costs:
            if doc_id not in doctor_patient_costs:
                doctor_patient_costs[doc_id] = {}
            cost_val = float(cost or 0)
            doctor_patient_costs[doc_id][pat_id] = cost_val
            patient_total_costs[pat_id] = patient_total_costs.get(pat_id, 0) + cost_val

        # 5. Payments
        stmt = (
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
                models.Payment.doctor_id.isnot(None),
            )
        )
        if patient_id:
            stmt = stmt.where(models.Payment.patient_id == patient_id)
        payments_with_doctor = (await self.db.execute(stmt)).all()

        doctor_payments_direct = {}
        for doc_id, pat_id, amount in payments_with_doctor:
            if doc_id:
                doctor_payments_direct[doc_id] = doctor_payments_direct.get(
                    doc_id, 0
                ) + float(amount or 0)

        stmt = (
            select(models.Payment.patient_id, models.Payment.amount)
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
        payments_all = (await self.db.execute(stmt)).all()

        # 6. Build Result
        doctors = []
        for user in relevant_users:
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
            lab_cost = lab_cost_map.get(doctor_id, 0.0)

            # Collected Calculation
            collected = doctor_payments_direct.get(doctor_id, 0.0)

            # Fallback for payments without doctor_id using ratio
            payments_without_doctor = {}
            for pat_id, amount in payments_all:
                has_doctor_payments = any(
                    pat_id2 == pat_id and doc_id is not None
                    for doc_id, pat_id2, _ in payments_with_doctor
                )
                if not has_doctor_payments:
                    payments_without_doctor[pat_id] = payments_without_doctor.get(
                        pat_id, 0
                    ) + float(amount or 0)

            doc_patients = doctor_patient_costs.get(doctor_id, {})
            for pat_id, doc_cost in doc_patients.items():
                if pat_id in payments_without_doctor:
                    total_cost = patient_total_costs.get(pat_id, 0)
                    if total_cost > 0:
                        ratio = doc_cost / total_cost
                        collected += payments_without_doctor[pat_id] * ratio

            collected = round(collected, 2)
            net_revenue = stats["revenue"] - lab_cost
            commission_percent = user.commission_percent or 0.0
            fixed_salary = user.fixed_salary or 0.0
            commission_base = max(0.0, collected - lab_cost)
            commission_amount = round(commission_base * (commission_percent / 100.0), 2)
            total_due = round(commission_amount + fixed_salary, 2)

            doctors.append(
                {
                    "doctor_id": doctor_id,
                    "doctor_name": user.username,
                    "treatments": stats["treatment_count"],
                    "gross_cost": stats["gross_cost"],
                    "patient_discount": stats["total_discount"],
                    "revenue": stats["revenue"],
                    "collected": collected,
                    "lab_cost": lab_cost,
                    "net_revenue": net_revenue,
                    "commission_base": commission_base,
                    "commission_percent": commission_percent,
                    "commission_amount": commission_amount,
                    "fixed_salary": fixed_salary,
                    "total_due": total_due,
                }
            )

        return doctors

    async def get_doctor_details_data(
        self, doctor_id: int, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        """Get detailed breakdown for a specific doctor with unified compensation contract."""
        stmt = select(models.User).where(
            models.User.id == doctor_id,
            models.User.tenant_id == self.tenant_id,
        )
        doctor = (await self.db.execute(stmt)).scalar_one_or_none()
        if not doctor:
            return None

        # Fetch treatments for this doctor in date range
        stmt = (
            select(models.Treatment, models.Patient.name)
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Treatment.doctor_id == doctor_id,
                models.Treatment.date >= start,
                models.Treatment.date <= end,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            .order_by(models.Treatment.date.desc())
        )
        treatments = (await self.db.execute(stmt)).all()

        # Fetch lab orders for this doctor in date range
        stmt = (
            select(models.LabOrder, models.Patient.name)
            .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
            .where(
                models.LabOrder.doctor_id == doctor_id,
                models.LabOrder.order_date >= start,
                models.LabOrder.order_date <= end,
                models.LabOrder.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            .order_by(models.LabOrder.order_date.desc())
        )
        lab_orders = (await self.db.execute(stmt)).all()

        # Unify with authoritative revenue analytics
        analytics_list = await self.get_doctor_revenue_analytics(start, end)
        doc_stat = next((d for d in analytics_list if d["doctor_id"] == doctor_id), None)

        total_revenue = doc_stat["revenue"] if doc_stat else 0.0
        total_collected = doc_stat["collected"] if doc_stat else 0.0
        total_lab_cost = doc_stat["lab_cost"] if doc_stat else 0.0
        commission_percent = doctor.commission_percent or 0.0
        fixed_salary = doctor.fixed_salary or 0.0
        commission_base = max(0.0, total_collected - total_lab_cost)
        commission_amount = round(commission_base * (commission_percent / 100.0), 2)
        total_due = round(commission_amount + fixed_salary, 2)

        return {
            "doctor_id": doctor.id,
            "doctor_name": doctor.username,
            "commission_percent": commission_percent,
            "fixed_salary": fixed_salary,
            "revenue": total_revenue,
            "total_revenue": total_revenue,
            "collected": total_collected,
            "total_collected": total_collected,
            "lab_cost": total_lab_cost,
            "total_lab_cost": total_lab_cost,
            "net_revenue": total_revenue - total_lab_cost,
            "commission_base": commission_base,
            "commission_amount": commission_amount,
            "total_due": total_due,
            "treatments": [
                {
                    "id": t.id,
                    "date": t.date,
                    "procedure": t.procedure,
                    "cost": t.cost,
                    "discount": t.discount,
                    "net": t.cost - t.discount,
                    "patient_id": t.patient_id,
                    "patient_name": patient_name,
                }
                for t, patient_name in treatments
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

    async def update_staff_compensation_settings(
        self,
        user_id: int,
        current_user: models.User,
        commission: float,
        salary: float,
        fee: float,
    ) -> bool:
        """Update compensation settings for a staff member."""
        stmt = select(models.User).where(
            models.User.id == user_id,
            models.User.tenant_id == self.tenant_id
        )
        user = (await self.db.execute(stmt)).scalar_one_or_none()

        if not user:
            return False

        old_values = {
            "commission_percent": user.commission_percent,
            "fixed_salary": user.fixed_salary,
            "per_appointment_fee": user.per_appointment_fee,
        }

        user.commission_percent = commission
        user.fixed_salary = salary
        user.per_appointment_fee = fee

        log_admin_action(
            self.db,
            current_user,
            "update",
            "compensation",
            target_user_id=user_id,
            old_value=old_values,
            new_value={
                "commission_percent": commission,
                "fixed_salary": salary,
                "per_appointment_fee": fee,
            },
        )
        await self.db.commit()
        return True

    async def get_staff_list_revenue(self) -> List[Dict[str, Any]]:
        """Get revenue settings for non-doctor staff."""
        stmt = select(models.User).where(
            models.User.tenant_id == self.tenant_id,
            models.User.role.notin_(DOCTOR_ROLES + ["super_admin", "admin"]),
        )
        staff = (await self.db.execute(stmt)).scalars().all()
        return [
            {
                "id": s.id,
                "username": s.username,
                "role": s.role,
                "commission_percent": s.commission_percent or 0,
                "fixed_salary": s.fixed_salary or 0,
                "per_appointment_fee": s.per_appointment_fee or 0,
            }
            for s in staff
        ]

    async def calculate_staff_dues(
        self, start: datetime, end: datetime, total_appointments: int
    ) -> tuple[List[Dict[str, Any]], float]:
        """Calculate dues for staff based on fixed salary and appointment fees."""
        # Only explicitly approved employee roles (exclude doctors, admins, super_admins, patients, guests)
        eligible_roles = ["receptionist", "nurse", "assistant", "accountant"]
        stmt = select(models.User).where(
            models.User.tenant_id == self.tenant_id,
            models.User.role.in_(eligible_roles),
        )
        staff_members = (await self.db.execute(stmt)).scalars().all()

        staff_dues = []
        total_staff_dues = 0.0

        for s in staff_members:
            fixed_salary = s.fixed_salary or 0.0
            per_appointment = s.per_appointment_fee or 0.0
            appointment_earnings = per_appointment * total_appointments
            total_due = fixed_salary + appointment_earnings

            staff_dues.append(
                {
                    "id": s.id,
                    "name": s.username,
                    "role": s.role,
                    "fixed_salary": fixed_salary,
                    "per_appointment_fee": per_appointment,
                    "appointments_in_period": total_appointments,
                    "appointment_earnings": appointment_earnings,
                    "total_due": total_due,
                }
            )
            total_staff_dues += total_due

        return staff_dues, total_staff_dues

    async def get_salary_status_for_month(self, month: str) -> Dict[str, Any]:
        """Get salary payment status for all eligible employees for a specific month (§16 MASTER_SPEC, GEMINI_REPAIR_PLAN R3)."""
        from calendar import monthrange
        from collections import defaultdict

        try:
            year, mon = map(int, month.split("-"))
            days_in_month = monthrange(year, mon)[1]
        except Exception:
            raise ValueError("Invalid month format. Expected YYYY-MM")

        # Explicitly approved payroll-eligible roles only
        eligible_roles = ["receptionist", "nurse", "assistant", "accountant"]
        stmt = select(models.User).where(
            models.User.tenant_id == self.tenant_id,
            models.User.role.in_(eligible_roles),
        )
        employees = (await self.db.execute(stmt)).scalars().all()

        # Fetch all salary payments for this tenant and month (supporting partial payment history)
        stmt_p = select(models.SalaryPayment).where(
            models.SalaryPayment.tenant_id == self.tenant_id,
            models.SalaryPayment.month == month,
        ).order_by(models.SalaryPayment.payment_date.asc(), models.SalaryPayment.id.asc())
        payments = (await self.db.execute(stmt_p)).scalars().all()

        payments_by_user = defaultdict(list)
        for p in payments:
            payments_by_user[p.user_id].append(p)

        result = []
        for emp in employees:
            base_salary = float(emp.fixed_salary or 0.0)

            # Prorated calculation
            is_new_this_month = False
            days_worked = days_in_month
            prorated_salary = base_salary

            if emp.hire_date:
                hire_date = emp.hire_date
                if isinstance(hire_date, str):
                    hire_date = datetime.strptime(hire_date, "%Y-%m-%d").date()
                if hire_date.year == year and hire_date.month == mon:
                    is_new_this_month = True
                    days_worked = max(1, days_in_month - hire_date.day + 1)
                    prorated_salary = base_salary * (days_worked / days_in_month)

            emp_payments = payments_by_user.get(emp.id, [])
            total_paid_for_emp = sum(float(p.amount or 0.0) for p in emp_payments)
            payable_amount = round(prorated_salary, 2)
            paid_amount = round(total_paid_for_emp, 2)
            remaining_amount = max(0.0, round(payable_amount - paid_amount, 2))

            if remaining_amount <= 0.001 and paid_amount > 0:
                status = "paid"
            elif paid_amount > 0:
                status = "partial"
            else:
                status = "unpaid"

            payments_history = [
                {
                    "id": p.id,
                    "amount": float(p.amount or 0.0),
                    "payment_date": p.payment_date.isoformat() if hasattr(p.payment_date, "isoformat") else str(p.payment_date),
                    "is_partial": p.is_partial,
                    "days_worked": p.days_worked,
                    "notes": p.notes,
                }
                for p in emp_payments
            ]

            latest_payment = payments_history[-1] if payments_history else None

            result.append(
                {
                    "id": emp.id,
                    "username": emp.username,
                    "role": emp.role,
                    "base_salary": base_salary,
                    "days_in_month": days_in_month,
                    "is_new_this_month": is_new_this_month,
                    "days_worked": days_worked,
                    "prorated_salary": payable_amount,
                    "payable_amount": payable_amount,
                    "paid_amount": paid_amount,
                    "remaining_amount": remaining_amount,
                    "status": status,
                    "hire_date": str(emp.hire_date) if emp.hire_date else None,
                    "payments": payments_history,
                    "payment": latest_payment,
                    "is_paid": status == "paid",
                }
            )

        return {"month": month, "employees": result}

    async def process_salary_payment(
        self,
        user_id: int,
        current_user: models.User,
        month: str,
        amount: float,
        is_partial: bool,
        days_worked: Optional[int],
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Record a salary payment with overpayment guards and multi-installment support."""
        from calendar import monthrange

        # Validate amount
        if amount is None or amount <= 0:
            return {"error": "يرجى إدخال مبلغ صحيح أكبر من صفر"}

        # Validate month
        try:
            year, mon = map(int, month.split("-"))
            days_in_month = monthrange(year, mon)[1]
        except Exception:
            return {"error": "صيغة الشهر غير صحيحة. يجب أن تكون YYYY-MM"}

        # Validate days worked if given
        if days_worked is not None and (days_worked < 1 or days_worked > 31):
            return {"error": "عدد الأيام المحتسبة غير صحيح (يجب أن يكون بين 1 و 31)"}

        # Check employee in tenant and eligible role
        eligible_roles = ["receptionist", "nurse", "assistant", "accountant"]
        stmt_emp = select(models.User).where(
            models.User.id == user_id,
            models.User.tenant_id == self.tenant_id,
            models.User.role.in_(eligible_roles),
        )
        emp = (await self.db.execute(stmt_emp)).scalar_one_or_none()
        if not emp:
            return {"error": "الموظف غير موجود أو غير مؤهل لمسير الرواتب"}

        # Compute payable amount
        base_salary = float(emp.fixed_salary or 0.0)
        prorated_salary = base_salary
        if emp.hire_date:
            hire_date = emp.hire_date
            if isinstance(hire_date, str):
                hire_date = datetime.strptime(hire_date, "%Y-%m-%d").date()
            if hire_date.year == year and hire_date.month == mon:
                effective_days = days_in_month - hire_date.day + 1
                prorated_salary = base_salary * (effective_days / days_in_month)

        payable_amount = round(prorated_salary, 2)

        # Existing paid payments for this employee & month
        stmt_existing = select(models.SalaryPayment).where(
            models.SalaryPayment.user_id == user_id,
            models.SalaryPayment.month == month,
            models.SalaryPayment.tenant_id == self.tenant_id,
        )
        existing_payments = (await self.db.execute(stmt_existing)).scalars().all()
        already_paid = sum(float(p.amount or 0.0) for p in existing_payments)

        # Overpayment guard: allow a tiny margin of 0.05 for floating point rounding
        if (already_paid + amount) > (payable_amount + 0.05):
            remaining = max(0.0, round(payable_amount - already_paid, 2))
            return {
                "error": f"المبلغ المطلوب ({amount}) يتجاوز المتبقي للراتب ({remaining}). الراتب المستحق: {payable_amount}، المسدد: {already_paid}"
            }

        # Determine if partial
        is_partial_actual = is_partial or ((already_paid + amount) < (payable_amount - 0.05))

        payment = models.SalaryPayment(
            user_id=user_id,
            month=month,
            amount=amount,
            is_partial=is_partial_actual,
            days_worked=days_worked or days_in_month,
            notes=notes,
            tenant_id=self.tenant_id,
        )
        self.db.add(payment)

        log_admin_action(
            self.db,
            current_user,
            "create",
            "salary_payment",
            target_user_id=user_id,
            new_value={
                "month": month,
                "amount": amount,
                "is_partial": is_partial_actual,
                "notes": notes,
            },
        )
        await self.db.commit()
        await self.db.refresh(payment)
        return {"success": True, "payment_id": payment.id}

    async def remove_salary_payment(self, payment_id: int, current_user: models.User) -> bool:
        """Delete a salary payment and automatically allow recalculation."""
        stmt = select(models.SalaryPayment).where(
            models.SalaryPayment.id == payment_id,
            models.SalaryPayment.tenant_id == self.tenant_id,
        )
        payment = (await self.db.execute(stmt)).scalar_one_or_none()

        if not payment:
            return False

        log_admin_action(
            self.db,
            current_user,
            "delete",
            "salary_payment",
            entity_id=payment_id,
            target_user_id=payment.user_id,
            old_value={"month": payment.month, "amount": payment.amount},
        )

        await self.db.delete(payment)
        await self.db.commit()
        return True

    async def update_employee_hire_date(
        self, user_id: int, hire_date_str: str, current_user: models.User
    ) -> bool:
        """Update employee hire date."""
        stmt = select(models.User).where(
            models.User.id == user_id,
            models.User.tenant_id == self.tenant_id
        )
        user = (await self.db.execute(stmt)).scalar_one_or_none()

        if not user:
            return False

        old_hire_date = str(user.hire_date) if user.hire_date else None

        try:
            user.hire_date = datetime.strptime(hire_date_str, "%Y-%m-%d").date()
            log_admin_action(
                self.db,
                current_user,
                "update",
                "hire_date",
                target_user_id=user_id,
                old_value={"hire_date": old_hire_date},
                new_value={"hire_date": hire_date_str},
            )
            await self.db.commit()
            return True
        except ValueError:
            return False

    async def get_patients_report(
        self,
        patient_id: Optional[int] = None,
        search: Optional[str] = None,
        outstanding_only: bool = False,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get patients financial report, with totals scoped to requested period or all-time."""
        # 1. All-time treatments subquery
        all_treatments_stmt = (
            select(
                models.Treatment.patient_id,
                func.coalesce(func.sum(models.Treatment.cost - models.Treatment.discount), 0.0).label("all_invoiced"),
            )
            .where(models.Treatment.is_deleted == False)
            .group_by(models.Treatment.patient_id)
        )
        all_treatments_sub = all_treatments_stmt.subquery()

        # 2. All-time payments subquery
        all_payments_stmt = (
            select(
                models.Payment.patient_id,
                func.coalesce(func.sum(models.Payment.amount), 0.0).label("all_paid"),
            )
            .group_by(models.Payment.patient_id)
        )
        all_payments_sub = all_payments_stmt.subquery()

        # 3. Period subqueries (if start and end specified)
        if start and end:
            period_treatments_stmt = (
                select(
                    models.Treatment.patient_id,
                    func.coalesce(func.sum(models.Treatment.cost - models.Treatment.discount), 0.0).label("period_invoiced"),
                )
                .where(
                    models.Treatment.is_deleted == False,
                    models.Treatment.date >= start,
                    models.Treatment.date <= end,
                )
                .group_by(models.Treatment.patient_id)
            )
            period_treatments_sub = period_treatments_stmt.subquery()

            period_payments_stmt = (
                select(
                    models.Payment.patient_id,
                    func.coalesce(func.sum(models.Payment.amount), 0.0).label("period_paid"),
                )
                .where(
                    models.Payment.date >= start,
                    models.Payment.date <= end,
                )
                .group_by(models.Payment.patient_id)
            )
            period_payments_sub = period_payments_stmt.subquery()
        else:
            period_treatments_sub = None
            period_payments_sub = None

        # Build main query selecting Patient and financial totals
        select_args = [
            models.Patient,
            func.coalesce(all_treatments_sub.c.all_invoiced, 0.0).label("all_invoiced"),
            func.coalesce(all_payments_sub.c.all_paid, 0.0).label("all_paid"),
        ]

        if start and end:
            select_args.extend([
                func.coalesce(period_treatments_sub.c.period_invoiced, 0.0).label("period_invoiced"),
                func.coalesce(period_payments_sub.c.period_paid, 0.0).label("period_paid"),
            ])

        stmt = (
            select(*select_args)
            .outerjoin(all_treatments_sub, models.Patient.id == all_treatments_sub.c.patient_id)
            .outerjoin(all_payments_sub, models.Patient.id == all_payments_sub.c.patient_id)
        )

        if start and end:
            stmt = stmt.outerjoin(period_treatments_sub, models.Patient.id == period_treatments_sub.c.patient_id)
            stmt = stmt.outerjoin(period_payments_sub, models.Patient.id == period_payments_sub.c.patient_id)

        stmt = stmt.where(
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False,
        )

        # Filters
        if search:
            search_pat = f"%{search}%"
            stmt = stmt.where(
                or_(
                    models.Patient.name.ilike(search_pat),
                    models.Patient.phone.ilike(search_pat),
                )
            )

        if patient_id:
            stmt = stmt.where(models.Patient.id == patient_id)
        elif outstanding_only:
            # Patients with positive outstanding balance (all-time)
            stmt = stmt.where(
                func.coalesce(all_treatments_sub.c.all_invoiced, 0.0) - func.coalesce(all_payments_sub.c.all_paid, 0.0) > 0
            )
        elif start and end:
            period_filter = or_(
                period_treatments_sub.c.patient_id.is_not(None),
                period_payments_sub.c.patient_id.is_not(None),
            )
            # Check period activity
            check_period_stmt = (
                select(models.Patient.id)
                .outerjoin(period_treatments_sub, models.Patient.id == period_treatments_sub.c.patient_id)
                .outerjoin(period_payments_sub, models.Patient.id == period_payments_sub.c.patient_id)
                .where(
                    models.Patient.tenant_id == self.tenant_id,
                    models.Patient.is_deleted == False,
                    period_filter,
                )
                .limit(1)
            )
            has_period_activity = (await self.db.execute(check_period_stmt)).scalar() is not None
            if has_period_activity:
                stmt = stmt.where(period_filter)
            else:
                # If no activity in this specific date range, show patients with any financial history
                stmt = stmt.where(
                    or_(
                        all_treatments_sub.c.patient_id.is_not(None),
                        all_payments_sub.c.patient_id.is_not(None),
                    )
                )
        else:
            # No date filter: show patients with any financial history
            stmt = stmt.where(
                or_(
                    all_treatments_sub.c.patient_id.is_not(None),
                    all_payments_sub.c.patient_id.is_not(None),
                )
            )

        report_subquery = stmt.order_by(None).subquery()
        count_stmt = select(func.count()).select_from(report_subquery)
        total_count = (await self.db.execute(count_stmt)).scalar() or 0

        period_invoiced_col = (
            report_subquery.c.period_invoiced if start and end else report_subquery.c.all_invoiced
        )
        period_paid_col = (
            report_subquery.c.period_paid if start and end else report_subquery.c.all_paid
        )
        all_time_balance = report_subquery.c.all_invoiced - report_subquery.c.all_paid
        summary_stmt = select(
            func.coalesce(func.sum(period_invoiced_col), 0.0),
            func.coalesce(func.sum(period_paid_col), 0.0),
            func.coalesce(func.sum(period_invoiced_col - period_paid_col), 0.0),
            func.coalesce(
                func.sum(case((all_time_balance > 0, all_time_balance), else_=0.0)),
                0.0,
            ),
        ).select_from(report_subquery)
        summary_row = (await self.db.execute(summary_stmt)).one()

        stmt = stmt.order_by(models.Patient.name.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        rows = res.all()

        patients_data = []
        for row in rows:
            patient = row[0]
            all_invoiced = float(row[1])
            all_paid = float(row[2])
            all_outstanding = max(0.0, all_invoiced - all_paid)

            if start and end:
                period_invoiced = float(row[3])
                period_paid = float(row[4])
                period_balance = period_invoiced - period_paid
            else:
                period_invoiced = all_invoiced
                period_paid = all_paid
                period_balance = all_outstanding

            patients_data.append({
                "patient_id": patient.id,
                "file_number": patient.file_number or patient.id,
                "patient_name": patient.name,
                "patient_phone": patient.phone,
                "total_invoiced": period_invoiced,
                "total_paid": period_paid,
                "outstanding_balance": period_balance if (start and end) else all_outstanding,
                "all_time_outstanding": all_outstanding,
            })

        return {
            "total": total_count,
            "summary": {
                "total_invoiced": float(summary_row[0]),
                "total_paid": float(summary_row[1]),
                "period_balance": float(summary_row[2]),
                "total_outstanding": float(summary_row[3]),
            },
            "patients": patients_data,
        }

    async def get_patient_financial_details(
        self,
        patient_id: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get a patient's full financial picture, optionally scoped to a date range."""
        stmt = select(models.Patient).where(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False,
        )
        patient = (await self.db.execute(stmt)).scalar_one_or_none()
        if not patient:
            return None

        # Applied known MissingGreenlet pattern fix: extract scalars immediately
        patient_name = patient.name
        patient_phone = patient.phone

        stmt_payments = (
            select(models.Payment)
            .where(
                models.Payment.patient_id == patient_id,
                models.Payment.tenant_id == self.tenant_id,
            )
            .order_by(models.Payment.date.desc())
        )
        if start and end:
            stmt_payments = stmt_payments.where(
                models.Payment.date >= start,
                models.Payment.date <= end,
            )
        res_payments = await self.db.execute(stmt_payments)
        payments = res_payments.scalars().all()

        payment_history = []
        total_paid = 0.0
        for p in payments:
            amount = float(p.amount or 0.0)
            total_paid += amount
            payment_history.append({
                "id": p.id,
                "date": str(p.date),
                "amount": amount,
                "notes": p.notes,
            })

        stmt_treatments = (
            select(models.Treatment)
            .where(
                models.Treatment.patient_id == patient_id,
                models.Treatment.tenant_id == self.tenant_id,
                models.Treatment.is_deleted == False,
            )
            .order_by(models.Treatment.date.desc())
        )
        if start and end:
            stmt_treatments = stmt_treatments.where(
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
        res_treatments = await self.db.execute(stmt_treatments)
        treatments = res_treatments.scalars().all()

        total_invoiced = 0.0
        treatment_history = []
        for t in treatments:
            cost = float(t.cost or 0.0)
            discount = float(t.discount or 0.0)
            net = cost - discount
            total_invoiced += net
            treatment_history.append({
                "id": t.id,
                "date": str(t.date),
                "procedure": t.procedure,
                "diagnosis": t.diagnosis,
                "cost": cost,
                "discount": discount,
                "net": net,
            })

        stmt_next_appt = (
            select(models.Appointment)
            .where(
                models.Appointment.patient_id == patient_id,
                models.Appointment.tenant_id == self.tenant_id,
                models.Appointment.date_time >= datetime.now(),
                models.Appointment.is_deleted == False,
            )
            .order_by(models.Appointment.date_time.asc())
            .limit(1)
        )
        res_next = await self.db.execute(stmt_next_appt)
        next_appt = res_next.scalar_one_or_none()
        next_due_date = str(next_appt.date_time) if next_appt else None

        return {
            "patient_id": patient_id,
            "file_number": patient.file_number or patient_id,
            "patient_name": patient_name,
            "patient_phone": patient_phone,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding_balance": max(0.0, total_invoiced - total_paid),
            "period_balance": total_invoiced - total_paid,
            "payment_history": payment_history,
            "treatment_history": treatment_history,
            "next_due_date": next_due_date,
        }

    async def get_financial_activity(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        current_user: Optional[models.User] = None,
    ) -> Dict[str, Any]:
        """
        Unified normalized financial activity timeline (§17 MASTER_SPEC, FIN-ACT-001, GEMINI_REPAIR_PLAN R2).
        Aggregates payments (inflow), expenses (outflow), lab orders (outflow), and salary payments (outflow).
        """
        start_dt = None
        end_dt = None
        if bool(start_date) != bool(end_date):
            raise ValueError("Both start_date and end_date are required when filtering by date")

        if start_date and end_date:
            start_dt, end_dt = self.parse_date_range(start_date, end_date)

        supported_types = {"payment", "expense", "lab", "salary"}
        if event_types:
            for t in event_types:
                if t not in supported_types:
                    raise ValueError(f"Unsupported event type: '{t}'. Must be one of {supported_types}")

        # Enforce RBAC visibility scope
        user_role = (current_user.role if current_user and current_user.role else "admin").lower()
        if user_role == "receptionist":
            allowed_types = {"payment"}
        elif user_role in {"doctor"}:
            allowed_types = {"payment"}
        else:
            allowed_types = supported_types

        types_set = (set(event_types) if event_types else supported_types).intersection(allowed_types)

        normalized_events = []
        fetch_limit = skip + limit
        total_count = 0
        total_inflow = 0.0
        total_outflow = 0.0

        async def get_source_totals(stmt, amount_column):
            """Aggregate a fully-filtered source query without loading its rows."""
            amounts_subquery = (
                stmt.with_only_columns(amount_column.label("amount"))
                .order_by(None)
                .subquery()
            )
            totals_stmt = select(
                func.count(),
                func.coalesce(func.sum(amounts_subquery.c.amount), 0.0),
            ).select_from(amounts_subquery)
            count, amount = (await self.db.execute(totals_stmt)).one()
            return int(count or 0), float(amount or 0.0)

        # 1. Payments (Inflow)
        if "payment" in types_set:
            p_stmt = (
                select(models.Payment, models.Patient)
                .outerjoin(models.Patient, models.Payment.patient_id == models.Patient.id)
                .where(models.Payment.tenant_id == self.tenant_id)
            )
            if user_role == "doctor" and current_user:
                p_stmt = p_stmt.where(models.Payment.doctor_id == current_user.id)

            if start_dt and end_dt:
                p_stmt = p_stmt.where(
                    models.Payment.date >= start_dt,
                    models.Payment.date <= end_dt
                )
            if search and search.strip():
                s = f"%{search.strip()}%"
                p_stmt = p_stmt.where(
                    or_(
                        models.Patient.name.ilike(s),
                        models.Payment.notes.ilike(s)
                    )
                )
            source_count, source_amount = await get_source_totals(p_stmt, models.Payment.amount)
            total_count += source_count
            total_inflow += source_amount
            p_stmt = p_stmt.order_by(
                models.Payment.date.desc(), models.Payment.id.desc()
            ).limit(fetch_limit)
            p_res = (await self.db.execute(p_stmt)).all()
            for payment, patient in p_res:
                patient_name = patient.name if patient else "مريض عام"
                p_date = payment.date
                ts = p_date.isoformat() if hasattr(p_date, "isoformat") else str(p_date)
                normalized_events.append({
                    "id": f"payment-{payment.id}",
                    "source_type": "payment",
                    "source_id": payment.id,
                    "timestamp": ts,
                    "direction": "inflow",
                    "amount": float(payment.amount or 0.0),
                    "currency": "EGP",
                    "title": patient_name,
                    "subtitle": payment.notes or "دفعة نقدية مسددة",
                    "badge_text": "دفعة مريض",
                    "nav_url": f"/finance/payments?patient_id={payment.patient_id}",
                    "patient_id": payment.patient_id,
                    "user_id": payment.doctor_id,
                })

        # 2. Manual Expenses (Outflow)
        if "expense" in types_set:
            e_stmt = select(models.Expense).where(models.Expense.tenant_id == self.tenant_id)
            if start_dt and end_dt:
                e_stmt = e_stmt.where(
                    models.Expense.date >= start_dt.date(),
                    models.Expense.date <= end_dt.date()
                )
            if search and search.strip():
                s = f"%{search.strip()}%"
                e_stmt = e_stmt.where(
                    or_(
                        models.Expense.category.ilike(s),
                        models.Expense.item_name.ilike(s),
                        models.Expense.notes.ilike(s)
                    )
                )
            source_count, source_amount = await get_source_totals(e_stmt, models.Expense.cost)
            total_count += source_count
            total_outflow += source_amount
            e_stmt = e_stmt.order_by(
                models.Expense.date.desc(), models.Expense.id.desc()
            ).limit(fetch_limit)
            e_res = (await self.db.execute(e_stmt)).scalars().all()
            for exp in e_res:
                e_date = exp.date
                ts = datetime.combine(e_date, datetime.min.time()).isoformat() if hasattr(e_date, "strftime") else str(e_date)
                normalized_events.append({
                    "id": f"expense-{exp.id}",
                    "source_type": "expense",
                    "source_id": exp.id,
                    "timestamp": ts,
                    "direction": "outflow",
                    "amount": float(exp.cost or 0.0),
                    "currency": "EGP",
                    "title": exp.item_name or exp.category or "مصروف تشغيلي",
                    "subtitle": exp.notes or exp.category or "مصروف مباشر",
                    "badge_text": "مصروف عيادة",
                    "nav_url": "/finance/expenses",
                    "patient_id": None,
                    "user_id": None,
                })

        # 3. Lab Orders (Outflow)
        if "lab" in types_set:
            l_stmt = (
                select(models.LabOrder, models.Patient)
                .outerjoin(models.Patient, models.LabOrder.patient_id == models.Patient.id)
                .where(
                    models.LabOrder.tenant_id == self.tenant_id,
                    models.LabOrder.cost > 0
                )
            )
            if start_dt and end_dt:
                l_stmt = l_stmt.where(
                    models.LabOrder.order_date >= start_dt,
                    models.LabOrder.order_date <= end_dt
                )
            if search and search.strip():
                s = f"%{search.strip()}%"
                l_stmt = l_stmt.where(
                    or_(
                        models.LabOrder.work_type.ilike(s),
                        models.Patient.name.ilike(s),
                        models.LabOrder.notes.ilike(s)
                    )
                )
            source_count, source_amount = await get_source_totals(l_stmt, models.LabOrder.cost)
            total_count += source_count
            total_outflow += source_amount
            l_stmt = l_stmt.order_by(
                models.LabOrder.order_date.desc(), models.LabOrder.id.desc()
            ).limit(fetch_limit)
            l_res = (await self.db.execute(l_stmt)).all()
            for lab_order, patient in l_res:
                patient_name = patient.name if patient else "مريض"
                ts = lab_order.order_date.isoformat() if lab_order.order_date else ""
                normalized_events.append({
                    "id": f"lab-{lab_order.id}",
                    "source_type": "lab",
                    "source_id": lab_order.id,
                    "timestamp": ts,
                    "direction": "outflow",
                    "amount": float(lab_order.cost or 0.0),
                    "currency": "EGP",
                    "title": f"معمل: {lab_order.work_type or 'تركيبة'}",
                    "subtitle": f"لحالة: {patient_name}",
                    "badge_text": "معمل أسنان",
                    "nav_url": "/labs",
                    "patient_id": lab_order.patient_id,
                    "user_id": None,
                })

        # 4. Salaries (Outflow)
        if "salary" in types_set:
            s_stmt = (
                select(models.SalaryPayment, models.User)
                .outerjoin(models.User, models.SalaryPayment.user_id == models.User.id)
                .where(models.SalaryPayment.tenant_id == self.tenant_id)
            )
            if start_dt and end_dt:
                s_stmt = s_stmt.where(
                    models.SalaryPayment.payment_date >= start_dt,
                    models.SalaryPayment.payment_date <= end_dt
                )
            if search and search.strip():
                s = f"%{search.strip()}%"
                s_stmt = s_stmt.where(
                    or_(
                        models.User.username.ilike(s),
                        models.SalaryPayment.notes.ilike(s)
                    )
                )
            source_count, source_amount = await get_source_totals(s_stmt, models.SalaryPayment.amount)
            total_count += source_count
            total_outflow += source_amount
            s_stmt = s_stmt.order_by(
                models.SalaryPayment.payment_date.desc(), models.SalaryPayment.id.desc()
            ).limit(fetch_limit)
            s_res = (await self.db.execute(s_stmt)).all()
            for salary_payment, user in s_res:
                emp_name = user.username if user else "موظف"
                ts = salary_payment.payment_date.isoformat() if salary_payment.payment_date else ""
                normalized_events.append({
                    "id": f"salary-{salary_payment.id}",
                    "source_type": "salary",
                    "source_id": salary_payment.id,
                    "timestamp": ts,
                    "direction": "outflow",
                    "amount": float(salary_payment.amount or 0.0),
                    "currency": "EGP",
                    "title": f"راتب: {emp_name}",
                    "subtitle": salary_payment.notes or f"راتب شهر {salary_payment.month}",
                    "badge_text": "راتب موظف",
                    "nav_url": f"/finance/compensation/payroll?month={salary_payment.month}",
                    "patient_id": None,
                    "user_id": salary_payment.user_id,
                })

        # Sort all chronologically descending with stable tie-breaker on source_id
        normalized_events.sort(
            key=lambda x: (x["timestamp"] or "", x["source_id"] or 0),
            reverse=True,
        )

        net_flow = total_inflow - total_outflow

        paged_events = normalized_events[skip : skip + limit]

        return {
            "events": paged_events,
            "total_count": total_count,
            "total_inflow": round(total_inflow, 2),
            "total_outflow": round(total_outflow, 2),
            "net_flow": round(net_flow, 2),
            "skip": skip,
            "limit": limit,
        }
