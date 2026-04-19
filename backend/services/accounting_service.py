"""
Accounting Service for Smart Clinic Management System.

Handles all doctor revenue, compensation, and salary calculations.
Extracted from routers/accounting.py to follow service layer pattern.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Dict, Any

from backend import models
from backend.core.permissions import Role, DOCTOR_ROLES
from backend.utils.audit_logger import log_admin_action


class AccountingService:
    """Service for accounting and revenue calculations."""

    def __init__(self, db: Session, tenant_id: int):
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

    def get_relevant_users(self, roles: List[str] = None) -> List[models.User]:
        """Get all users with specified roles for the tenant."""
        if roles is None:
            roles = DOCTOR_ROLES
        return (
            self.db.query(models.User)
            .filter(
                models.User.tenant_id == self.tenant_id, models.User.role.in_(roles)
            )
            .all()
        )

    def get_treatment_stats_by_doctor(
        self, start: datetime, end: datetime, doctor_ids: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """Get treatment statistics grouped by doctor."""
        results = (
            self.db.query(
                models.Treatment.doctor_id,
                func.count(models.Treatment.id).label("treatment_count"),
                func.sum(models.Treatment.cost).label("gross_cost"),
                func.sum(models.Treatment.discount).label("total_discount"),
                func.sum(models.Treatment.cost - models.Treatment.discount).label(
                    "revenue"
                ),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start,
                models.Treatment.date <= end,
                models.Treatment.doctor_id.in_(doctor_ids) if doctor_ids else True,
            )
            .group_by(models.Treatment.doctor_id)
            .all()
        )

        return {
            r.doctor_id: {
                "treatment_count": r.treatment_count,
                "gross_cost": float(r.gross_cost or 0),
                "total_discount": float(r.total_discount or 0),
                "revenue": float(r.revenue or 0),
            }
            for r in results
        }

    def get_lab_costs_by_doctor(
        self, start: datetime, end: datetime, doctor_ids: List[int]
    ) -> Dict[int, float]:
        """Get lab costs grouped by doctor."""
        results = (
            self.db.query(
                models.LabOrder.doctor_id,
                func.sum(models.LabOrder.cost).label("lab_cost"),
            )
            .filter(
                models.LabOrder.tenant_id == self.tenant_id,
                models.LabOrder.order_date >= start,
                models.LabOrder.order_date <= end,
                models.LabOrder.doctor_id.in_(doctor_ids) if doctor_ids else True,
            )
            .group_by(models.LabOrder.doctor_id)
            .all()
        )

        return {r[0]: float(r[1] or 0) for r in results}

    def get_total_income(self, start: datetime, end: datetime) -> float:
        """Calculate total income from treatments in date range."""
        return float(
            self.db.query(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start,
                models.Treatment.date <= end,
            )
            .scalar()
            or 0.0
        )

    def get_total_collected(self, start: datetime, end: datetime) -> float:
        """Calculate total collected payments in date range."""
        return float(
            self.db.query(func.sum(models.Payment.amount))
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= start,
                models.Payment.date <= end,
            )
            .scalar()
            or 0.0
        )

    def get_total_expenses(self, start: datetime, end: datetime) -> float:
        """Calculate total expenses in date range."""
        return float(
            self.db.query(func.sum(models.Expense.cost))
            .filter(
                models.Expense.tenant_id == self.tenant_id,
                models.Expense.date >= start.date(),
                models.Expense.date <= end.date(),
            )
            .scalar()
            or 0.0
        )

    def get_total_lab_costs(self, start: datetime, end: datetime) -> float:
        """Calculate total lab costs in date range."""
        return float(
            self.db.query(func.sum(models.LabOrder.cost))
            .filter(
                models.LabOrder.tenant_id == self.tenant_id,
                models.LabOrder.order_date >= start,
                models.LabOrder.order_date <= end,
            )
            .scalar()
            or 0.0
        )

    def calculate_doctor_dues(
        self, start: datetime, end: datetime
    ) -> tuple[List[Dict[str, Any]], float]:
        """Calculate dues for all doctors in date range using COLLECTED amount."""
        # Use existing analytics to get accurate 'collected' amount
        doctors_analytics = self.get_doctor_revenue_analytics(start, end)

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

    def get_doctor_revenue_analytics(
        self, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get detailed revenue generated by each doctor, including:
        - Treatment counts/costs
        - Lab costs
        - Collected payments (with ratio calculation fallback)
        - Net revenue
        """
        # 1. Get ALL relevant users (Doctors + Admins)
        relevant_users = self.get_relevant_users(
            DOCTOR_ROLES + ["admin", "super_admin"]
        )
        relevant_user_ids = [u.id for u in relevant_users]

        # 2. Main Stats Query
        stats_map = self.get_treatment_stats_by_doctor(start, end, relevant_user_ids)

        # 3. Lab Costs
        lab_cost_map = self.get_lab_costs_by_doctor(start, end, relevant_user_ids)

        # 4. Treatment Costs per Patient (for ratio calculation)
        treatment_costs = (
            self.db.query(
                models.Treatment.doctor_id,
                models.Treatment.patient_id,
                func.sum(models.Treatment.cost).label("cost"),
            )
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.date >= start,
                models.Treatment.date <= end,
                models.Treatment.doctor_id.in_(relevant_user_ids)
                if relevant_user_ids
                else True,
            )
            .group_by(models.Treatment.doctor_id, models.Treatment.patient_id)
            .all()
        )

        doctor_patient_costs = {}
        patient_total_costs = {}
        for doc_id, pat_id, cost in treatment_costs:
            if doc_id not in doctor_patient_costs:
                doctor_patient_costs[doc_id] = {}
            cost_val = float(cost or 0)
            doctor_patient_costs[doc_id][pat_id] = cost_val
            patient_total_costs[pat_id] = patient_total_costs.get(pat_id, 0) + cost_val

        # 5. Payments
        payments_with_doctor = (
            self.db.query(
                models.Payment.doctor_id,
                models.Payment.patient_id,
                models.Payment.amount,
            )
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= start,
                models.Payment.date <= end,
                models.Payment.doctor_id.isnot(None),
            )
            .all()
        )

        doctor_payments_direct = {}
        for doc_id, pat_id, amount in payments_with_doctor:
            if doc_id:
                doctor_payments_direct[doc_id] = doctor_payments_direct.get(
                    doc_id, 0
                ) + float(amount or 0)

        payments_all = (
            self.db.query(models.Payment.patient_id, models.Payment.amount)
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Payment.date >= start,
                models.Payment.date <= end,
            )
            .all()
        )

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
                    "commission_percent": user.commission_percent or 0,
                    "fixed_salary": user.fixed_salary or 0,
                }
            )

        return doctors

    def get_doctor_details_data(
        self, doctor_id: int, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        """Get detailed breakdown for a specific doctor."""
        doctor = self.db.query(models.User).filter(models.User.id == doctor_id).first()
        if not doctor:
            return None

        treatments = (
            self.db.query(models.Treatment, models.Patient.name)
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .filter(
                models.Treatment.doctor_id == doctor_id,
                models.Treatment.date >= start,
                models.Treatment.date <= end,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            .all()
        )

        lab_orders = (
            self.db.query(models.LabOrder, models.Patient.name)
            .join(models.Patient, models.LabOrder.patient_id == models.Patient.id)
            .filter(
                models.LabOrder.doctor_id == doctor_id,
                models.LabOrder.order_date >= start,
                models.LabOrder.order_date <= end,
                models.LabOrder.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            .all()
        )

        return {
            "doctor_name": doctor.username,
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

    def update_staff_compensation_settings(
        self,
        user_id: int,
        current_user: models.User,
        commission: float,
        salary: float,
        fee: float,
    ) -> bool:
        """Update compensation settings for a staff member."""
        user = (
            self.db.query(models.User)
            .filter(models.User.id == user_id, models.User.tenant_id == self.tenant_id)
            .first()
        )

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
        self.db.commit()
        return True

    def get_staff_list_revenue(self) -> List[Dict[str, Any]]:
        """Get revenue settings for non-doctor staff."""
        staff = (
            self.db.query(models.User)
            .filter(
                models.User.tenant_id == self.tenant_id,
                models.User.role.notin_(DOCTOR_ROLES + ["super_admin", "admin"]),
            )
            .all()
        )
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

    def calculate_staff_dues(
        self, start: datetime, end: datetime, total_appointments: int
    ) -> tuple[List[Dict[str, Any]], float]:
        """Calculate dues for staff based on fixed salary and appointment fees."""
        staff_members = (
            self.db.query(models.User)
            .filter(
                models.User.tenant_id == self.tenant_id,
                models.User.role.notin_(DOCTOR_ROLES + ["super_admin", "admin"]),
            )
            .all()
        )

        staff_dues = []
        total_staff_dues = 0.0

        for s in staff_members:
            fixed_salary = s.fixed_salary or 0
            per_appointment = s.per_appointment_fee or 0
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

    def get_salary_status_for_month(self, month: str) -> Dict[str, Any]:
        """Get salary payment status for all employees for a specific month."""
        from calendar import monthrange

        try:
            year, mon = map(int, month.split("-"))
            days_in_month = monthrange(year, mon)[1]
        except Exception:
            raise ValueError("Invalid month format")

        employees = (
            self.db.query(models.User)
            .filter(
                models.User.tenant_id == self.tenant_id,
                models.User.role != "super_admin",
            )
            .all()
        )

        payments = (
            self.db.query(models.SalaryPayment)
            .filter(
                models.SalaryPayment.tenant_id == self.tenant_id,
                models.SalaryPayment.month == month,
            )
            .all()
        )
        payments_map = {p.user_id: p for p in payments}

        result = []
        for emp in employees:
            payment = payments_map.get(emp.id)
            base_salary = emp.fixed_salary or 0

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
                    days_worked = days_in_month - hire_date.day + 1
                    prorated_salary = base_salary * (days_worked / days_in_month)

            result.append(
                {
                    "id": emp.id,
                    "username": emp.username,
                    "role": emp.role,
                    "base_salary": base_salary,
                    "days_in_month": days_in_month,
                    "is_new_this_month": is_new_this_month,
                    "days_worked": days_worked,
                    "prorated_salary": round(prorated_salary, 2),
                    "hire_date": str(emp.hire_date) if emp.hire_date else None,
                    "payment": {
                        "id": payment.id,
                        "amount": payment.amount,
                        "payment_date": str(payment.payment_date),
                        "is_partial": payment.is_partial,
                        "notes": payment.notes,
                    }
                    if payment
                    else None,
                    "is_paid": payment is not None,
                }
            )
        return {"month": month, "employees": result}

    def process_salary_payment(
        self,
        user_id: int,
        current_user: models.User,
        month: str,
        amount: float,
        is_partial: bool,
        days_worked: int,
        notes: str,
    ) -> Dict[str, Any]:
        """Record a salary payment."""
        existing = (
            self.db.query(models.SalaryPayment)
            .filter(
                models.SalaryPayment.user_id == user_id,
                models.SalaryPayment.month == month,
                models.SalaryPayment.tenant_id == self.tenant_id,
            )
            .first()
        )

        if existing:
            return {"error": "Paid already", "payment_id": existing.id}

        payment = models.SalaryPayment(
            user_id=user_id,
            month=month,
            amount=amount,
            is_partial=is_partial,
            days_worked=days_worked,
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
                "is_partial": is_partial,
                "notes": notes,
            },
        )
        self.db.commit()
        self.db.refresh(payment)
        return {"success": True, "payment_id": payment.id}

    def remove_salary_payment(self, payment_id: int, current_user: models.User) -> bool:
        """Delete a salary payment."""
        payment = (
            self.db.query(models.SalaryPayment)
            .filter(
                models.SalaryPayment.id == payment_id,
                models.SalaryPayment.tenant_id == self.tenant_id,
            )
            .first()
        )

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

        self.db.delete(payment)
        self.db.commit()
        return True

    def update_employee_hire_date(
        self, user_id: int, hire_date_str: str, current_user: models.User
    ) -> bool:
        """Update employee hire date."""
        user = (
            self.db.query(models.User)
            .filter(models.User.id == user_id, models.User.tenant_id == self.tenant_id)
            .first()
        )

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
            self.db.commit()
            return True
        except ValueError:
            return False
