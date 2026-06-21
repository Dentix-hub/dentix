"""
Financial Visibility Service (Multi-Doctor Support)

This service determines which financial data a user can see:
- Payments
- Expenses
- Treatment costs

SECURITY: Financial data is strictly controlled per doctor.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select
from typing import Optional
from backend.models import User, Patient, Payment, Treatment
import logging

logger = logging.getLogger(__name__)


def _doctor_can_view_all_patients(user: User) -> bool:
    """
    Whether a doctor is permitted to see financial data for ALL patients in the
    tenant, not just their own assigned patients.

    This reads the admin-settable `can_view_other_doctors_history` flag, which is
    the established per-doctor toggle for cross-doctor patient-finance visibility.
    """
    return bool(getattr(user, "can_view_other_doctors_history", False))


class FinancialVisibilityService:
    """
    Central service for financial data visibility.

    Rules:
    - Admin sees all financial data
    - Accountant sees all financial data
    - Doctor sees only their own financial data
    - Other roles: limited or no access
    """

    def __init__(self, db: AsyncSession, user: User, tenant_id: int):
        self.db = db
        self.user = user
        self.tenant_id = tenant_id

    def get_visible_payments_query(self):
        """
        Get filtered query for visible payments.

        Returns:
            SQLAlchemy Select filtered by user permissions
        """
        base_query = (
            select(Payment)
            .join(Payment.patient)
            .options(joinedload(Payment.patient))
            .where(
                Payment.tenant_id == self.tenant_id,
                Payment.patient.has(is_deleted=False),
            )
        )

        # Admin and Accountant see all
        if self.user.role in ["admin", "accountant"]:
            return base_query

        # Doctor visibility mirrors the patient-list semantics: a doctor sees
        # financial data for patients *assigned to them* (Patient.assigned_doctor_id),
        # NOT for payments stamped with their own id at creation time. This matters
        # when an admin reassigns an existing patient to a doctor — the patient then
        # shows up in the patient list (driven by assigned_doctor_id), and their
        # finances must follow the same field. If the doctor has been granted the
        # `can_view_other_doctors_history` override, they see all tenant finances.
        if self.user.role == "doctor":
            if _doctor_can_view_all_patients(self.user):
                return base_query
            return base_query.where(Patient.assigned_doctor_id == self.user.id)

        # Default: no access (empty query)
        return base_query.where(Payment.id == -1)

    def get_visible_treatments_query(self):
        """
        Get filtered query for visible treatments (cost perspective).

        Returns:
            SQLAlchemy Select filtered by user permissions
        """
        base_query = (
            select(Treatment)
            .join(Treatment.patient)
            .where(
                Treatment.tenant_id == self.tenant_id,
                Treatment.patient.has(is_deleted=False),
            )
        )

        # Admin and Accountant see all
        if self.user.role in ["admin", "accountant"]:
            return base_query

        # Doctor: see treatments for patients assigned to them (same field as the
        # patient list), or all if granted the cross-doctor history override.
        if self.user.role == "doctor":
            if _doctor_can_view_all_patients(self.user):
                return base_query
            return base_query.where(Patient.assigned_doctor_id == self.user.id)

        # Nurse: read-only all treatments
        if self.user.role == "nurse":
            return base_query

        # Default: empty
        return base_query.where(Treatment.id == -1)

    def can_view_payment(self, payment: Payment) -> bool:
        """Check if user can view a specific payment."""
        if self.user.role in ["admin", "accountant"]:
            return True

        if self.user.role == "doctor":
            # Cross-doctor override: admin granted full patient-finance visibility.
            if _doctor_can_view_all_patients(self.user):
                return True
            # Otherwise: same field as the patient list (Patient.assigned_doctor_id).
            # Access defensively — `patient` may be unloaded on an unrefreshed row.
            assigned_id = getattr(getattr(payment, "patient", None), "assigned_doctor_id", None)
            return assigned_id == self.user.id

        return False

    async def get_doctor_revenue(self, doctor_id: Optional[int] = None) -> float:
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

        stmt = (
            select(Payment.amount)
            .where(Payment.tenant_id == self.tenant_id, Payment.doctor_id == target_id)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return sum(r.amount for r in rows) if rows else 0.0


def get_financial_visibility_service(
    db: AsyncSession, user: User, tenant_id: int
) -> FinancialVisibilityService:
    """Factory function to create financial visibility service."""
    return FinancialVisibilityService(db, user, tenant_id)
