"""
Financial Visibility Service (Multi-Doctor Support)

This service determines which financial data a user can see:
- Payments
- Expenses
- Treatment costs

SECURITY: Financial data is strictly controlled per doctor.
"""

from sqlalchemy.orm import Session, Query, joinedload
from typing import Optional
from backend.models import User, Payment, Treatment
import logging

logger = logging.getLogger(__name__)


class FinancialVisibilityService:
    """
    Central service for financial data visibility.

    Rules:
    - Admin sees all financial data
    - Accountant sees all financial data
    - Doctor sees only their own financial data
    - Other roles: limited or no access
    """

    def __init__(self, db: Session, user: User, tenant_id: int):
        self.db = db
        self.user = user
        self.tenant_id = tenant_id

    def get_visible_payments_query(self) -> Query:
        """
        Get filtered query for visible payments.

        Returns:
            SQLAlchemy Query filtered by user permissions
        """
        base_query = (
            self.db.query(Payment)
            .join(Payment.patient)
            .options(joinedload(Payment.patient))
            .filter(
                Payment.tenant_id == self.tenant_id,
                Payment.patient.has(is_deleted=False),
            )
        )

        # Admin and Accountant see all
        if self.user.role in ["admin", "accountant"]:
            return base_query

        # Doctor sees only their payments
        if self.user.role == "doctor":
            return base_query.filter(Payment.doctor_id == self.user.id)

        # Default: no access (empty query)
        return base_query.filter(Payment.id == -1)

    def get_visible_treatments_query(self) -> Query:
        """
        Get filtered query for visible treatments (cost perspective).

        Returns:
            SQLAlchemy Query filtered by user permissions
        """
        base_query = (
            self.db.query(Treatment)
            .join(Treatment.patient)
            .filter(
                Treatment.tenant_id == self.tenant_id,
                Treatment.patient.has(is_deleted=False),
            )
        )

        # Admin and Accountant see all
        if self.user.role in ["admin", "accountant"]:
            return base_query

        # Doctor sees only their treatments
        if self.user.role == "doctor":
            return base_query.filter(Treatment.doctor_id == self.user.id)

        # Nurse: read-only all treatments
        if self.user.role == "nurse":
            return base_query

        # Default: empty
        return base_query.filter(Treatment.id == -1)

    def can_view_payment(self, payment: Payment) -> bool:
        """Check if user can view a specific payment."""
        if self.user.role in ["admin", "accountant"]:
            return True

        if self.user.role == "doctor":
            return payment.doctor_id == self.user.id

        return False

    def get_doctor_revenue(self, doctor_id: Optional[int] = None) -> float:
        """
        Calculate revenue for a specific doctor or current user.

        Args:
            doctor_id: Optional doctor ID (defaults to current user)

        Returns:
            Total revenue amount
        """
        target_id = doctor_id or self.user.id

        # Only admin can see other doctors' revenue
        if target_id != self.user.id and self.user.role != "admin":
            return 0.0

        result = (
            self.db.query(Payment)
            .filter(Payment.tenant_id == self.tenant_id, Payment.doctor_id == target_id)
            .with_entities(Payment.amount)
            .all()
        )

        return sum(r.amount for r in result) if result else 0.0


def get_financial_visibility_service(
    db: Session, user: User, tenant_id: int
) -> FinancialVisibilityService:
    """Factory function to create financial visibility service."""
    return FinancialVisibilityService(db, user, tenant_id)
