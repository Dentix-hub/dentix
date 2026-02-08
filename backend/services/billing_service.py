"""
Billing Service (Refactored)

Financial calculations and payment processing for tenants.
Follows Single Responsibility Principle with extracted helper methods.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from typing import Optional
from backend import models, schemas
from backend.crud import billing as billing_crud


class BillingService:
    """Service layer for billing and financial operations."""
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self._today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    
    def _scalar(self, query) -> float:
        """Execute query and return scalar result as float, defaulting to 0.0."""
        return float(query.scalar() or 0.0)
    
    # --- Payment Operations ---
    def create_payment(self, payment: schemas.PaymentCreate, doctor_id: int = None):
        """
        Create a payment record.
        
        Business Rules:
        - Patient must belong to this tenant
        - Payment amount must be positive
        """
        patient = self.db.query(models.Patient).filter(
            models.Patient.id == payment.patient_id,
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False
        ).first()
        
        if not patient:
            raise ValueError("Patient not found")
        
        return billing_crud.create_payment(
            db=self.db,
            payment=payment,
            tenant_id=self.tenant_id,
            doctor_id=doctor_id
        )
    
    # --- Revenue Calculations ---
    def _calculate_revenue(self, for_today: bool = False) -> float:
        """
        Calculate revenue from treatments.
        Revenue = Cost - Discounts
        
        Args:
            for_today: If True, only calculate today's revenue
        """
        query = self.db.query(
            func.sum(models.Treatment.cost - models.Treatment.discount)
        ).join(models.Patient).filter(
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False
        )
        
        if for_today:
            query = query.filter(models.Treatment.date >= self._today_start)
        
        return self._scalar(query)
    
    def _calculate_total_cost(self) -> float:
        """Calculate total treatment cost (before discounts)."""
        return self._scalar(
            self.db.query(func.sum(models.Treatment.cost))
            .join(models.Patient)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False
            )
        )
    
    def _calculate_total_discount(self) -> float:
        """Calculate total discounts applied."""
        return self._scalar(
            self.db.query(func.sum(models.Treatment.discount))
            .join(models.Patient)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False
            )
        )
    
    def _calculate_monthly_revenue(self) -> float:
        """Calculate revenue for the current month."""
        # Get first day of current month
        today = datetime.utcnow()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return self._scalar(
            self.db.query(func.sum(models.Treatment.cost - models.Treatment.discount))
            .join(models.Patient)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Treatment.date >= month_start
            )
        )
    
    # --- Payment Calculations ---
    def _calculate_payments(self, for_today: bool = False) -> float:
        """
        Calculate total payments received.
        
        Args:
            for_today: If True, only calculate today's payments
        """
        query = self.db.query(
            func.sum(models.Payment.amount)
        ).join(models.Patient).filter(
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False
        )
        
        if for_today:
            query = query.filter(models.Payment.date >= self._today_start)
        
        return self._scalar(query)
    
    # --- Expense Calculations ---
    def _calculate_expenses(self, for_today: bool = False) -> dict:
        """
        Calculate expenses breakdown.
        
        Returns:
            dict with 'lab_costs' and 'other_expenses' keys
        """
        # Lab costs
        lab_query = self.db.query(
            func.sum(models.LabOrder.cost)
        ).filter(models.LabOrder.tenant_id == self.tenant_id)
        
        if for_today:
            lab_query = lab_query.filter(
                models.LabOrder.order_date >= self._today_start
            )
        
        lab_costs = self._scalar(lab_query)
        
        # Other expenses
        expense_query = self.db.query(
            func.sum(models.Expense.cost)
        ).filter(models.Expense.tenant_id == self.tenant_id)
        
        if for_today:
            expense_query = expense_query.filter(
                models.Expense.date == date.today()
            )
        
        other_expenses = self._scalar(expense_query)
        
        return {
            "lab_costs": lab_costs,
            "other_expenses": other_expenses,
            "total": lab_costs + other_expenses
        }
    
    # --- Aggregate Statistics ---
    def get_financial_stats(self) -> dict:
        """
        Get comprehensive financial statistics for the tenant.
        
        Returns aggregated data from all sub-calculations.
        """
        # Revenue
        total_cost = self._calculate_total_cost()
        total_discount = self._calculate_total_discount()
        total_revenue = total_cost - total_discount
        today_revenue = self._calculate_revenue(for_today=True)
        
        # Payments
        total_received = self._calculate_payments()
        today_received = self._calculate_payments(for_today=True)
        
        # Outstanding
        outstanding = max(0, total_revenue - total_received)
        today_outstanding = max(0, today_revenue - today_received)
        
        # Expenses
        all_expenses = self._calculate_expenses()
        today_expenses = self._calculate_expenses(for_today=True)
        
        # Profit
        net_profit = total_received - all_expenses["total"]
        
        return {
            "total_revenue": total_revenue,
            "total_received": total_received,
            "outstanding": outstanding,
            "total_expenses": all_expenses["total"],
            "net_profit": net_profit,
            "monthly_revenue": self._calculate_monthly_revenue(),
            "today_revenue": today_revenue,
            "today_received": today_received,
            "today_outstanding": today_outstanding,
            "today_expenses": today_expenses["total"],
        }
    
    def get_outstanding_balance(self, patient_id: Optional[int] = None) -> float:
        """
        Get outstanding balance for a patient or entire tenant.
        
        Args:
            patient_id: If provided, calculate for specific patient only
        """
        # Revenue query
        revenue_query = self.db.query(
            func.sum(models.Treatment.cost - models.Treatment.discount)
        ).join(models.Patient).filter(
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False
        )
        
        # Payment query
        payment_query = self.db.query(
            func.sum(models.Payment.amount)
        ).join(models.Patient).filter(
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted == False
        )
        
        if patient_id:
            revenue_query = revenue_query.filter(models.Treatment.patient_id == patient_id)
            payment_query = payment_query.filter(models.Payment.patient_id == patient_id)
        
        revenue = self._scalar(revenue_query)
        payments = self._scalar(payment_query)
        
        return max(0, revenue - payments)

    def get_today_payments_list(self) -> list:
        """Get list of payments made today."""
        results = (
            self.db.query(models.Payment, models.Patient.name)
            .join(models.Patient)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Payment.date >= self._today_start
            )
            .order_by(models.Payment.date.desc())
            .all()
        )
        
        return [
            {
                "id": p.id,
                "amount": p.amount,
                "date": p.date,
                "patient_name": name,
                "notes": p.notes
            }
            for p, name in results
        ]

    def get_today_debtors_list(self) -> list:
        """Get list of patients who incurred debt today (Treatment Cost Today > Payment Today)."""
        # 1. Get patients with treatments today
        today_treatments = (
            self.db.query(models.Treatment)
            .join(models.Patient)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,
                models.Treatment.date >= self._today_start
            )
            .all()
        )
        
        patient_ids = set(t.patient_id for t in today_treatments)
        debtors = []
        
        for pid in patient_ids:
            # Calculate today's cost for this patient
            cost = self._scalar(
                self.db.query(func.sum(models.Treatment.cost - models.Treatment.discount))
                .filter(
                    models.Treatment.patient_id == pid,
                    models.Treatment.date >= self._today_start
                )
            )
            
            # Calculate today's payment for this patient
            paid = self._scalar(
                self.db.query(func.sum(models.Payment.amount))
                .filter(
                    models.Payment.patient_id == pid,
                    models.Payment.date >= self._today_start
                )
            )
            
            balance = cost - paid
            if balance > 0:
                patient = self.db.query(models.Patient).get(pid)
                debtors.append({
                    "id": patient.id,
                    "name": patient.name,
                    "phone": str(patient.phone), # basic serialization
                    "amount": balance,
                    "total_cost": cost,
                    "total_paid": paid
                })
        
        return debtors
