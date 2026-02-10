"""
Pricing Service (Multi Price List Support)

Central service for all pricing operations:
- Get procedure prices from price lists
- Apply prices to treatments (with snapshot)
- Calculate insurance vs patient share

SECURITY: Price access respects user permissions.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import date
import json
import logging

from backend.models import PriceList, PriceListItem, Procedure, Treatment, User
from backend.core.permissions import Role

logger = logging.getLogger(__name__)


class PricingService:
    """Central pricing logic - SINGLE SOURCE OF TRUTH."""

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # --- Price Lists ---

    def get_default_price_list(self) -> Optional[PriceList]:
        """Get default (cash) price list for tenant."""
        return (
            self.db.query(PriceList)
            .filter(
                PriceList.tenant_id == self.tenant_id,
                PriceList.is_default == True,
                PriceList.is_active == True,
            )
            .first()
        )

    def get_price_list(self, price_list_id: int) -> Optional[PriceList]:
        """Get a specific price list."""
        return (
            self.db.query(PriceList)
            .filter(
                PriceList.id == price_list_id, PriceList.tenant_id == self.tenant_id
            )
            .first()
        )

    def get_available_price_lists(
        self, user: User, include_inactive: bool = False
    ) -> List[PriceList]:
        """Get price lists available for user's role."""
        query = self.db.query(PriceList).filter(PriceList.tenant_id == self.tenant_id)

        if not include_inactive:
            query = query.filter(PriceList.is_active == True)

        # Admin sees all
        if user.role == Role.ADMIN.value:
            return query.all()

        # Accountant sees all
        if user.role == Role.ACCOUNTANT.value:
            return query.all()

        # Doctor/Staff: only active cash + allowed insurance
        # For now, return all active (can add restrictions later)
        return query.all()

    # --- Procedure Pricing ---

    def get_procedure_price(
        self, procedure_id: int, price_list_id: Optional[int] = None
    ) -> float:
        """
        Get price for procedure from specific list.

        Fallback order:
        1. PriceListItem in specified list
        2. PriceListItem in default list
        3. Procedure.price (legacy)
        """
        # Try specified price list
        if price_list_id:
            item = (
                self.db.query(PriceListItem)
                .filter(
                    PriceListItem.price_list_id == price_list_id,
                    PriceListItem.procedure_id == procedure_id,
                )
                .first()
            )

            if item:
                return item.final_price

        # Try default price list
        default_list = self.get_default_price_list()
        if default_list:
            item = (
                self.db.query(PriceListItem)
                .filter(
                    PriceListItem.price_list_id == default_list.id,
                    PriceListItem.procedure_id == procedure_id,
                )
                .first()
            )

            if item:
                return item.final_price

        # Fallback to Procedure.price (legacy)
        procedure = (
            self.db.query(Procedure).filter(Procedure.id == procedure_id).first()
        )

        return procedure.price if procedure and procedure.price else 0.0

    def get_all_prices_for_procedure(self, procedure_id: int) -> List[Dict[str, Any]]:
        """Get price from all price lists for a procedure."""
        items = (
            self.db.query(PriceListItem)
            .join(PriceList)
            .filter(
                PriceListItem.procedure_id == procedure_id,
                PriceList.tenant_id == self.tenant_id,
                PriceList.is_active == True,
            )
            .all()
        )

        return [
            {
                "price_list_id": item.price_list_id,
                "price_list_name": item.price_list.name,
                "price_list_type": item.price_list.type,
                "price": item.price,
                "discount_percent": item.discount_percent,
                "final_price": item.final_price,
            }
            for item in items
        ]

    # --- Treatment Pricing ---

    def apply_price_to_treatment(
        self,
        treatment: Treatment,
        price_list_id: Optional[int] = None,
        procedure_id: Optional[int] = None,
    ) -> Treatment:
        """
        Apply pricing to treatment and create snapshot.

        Args:
            treatment: Treatment object to update
            price_list_id: Price list to use (optional)
            procedure_id: Procedure ID for price lookup
        """
        # Determine price list
        if not price_list_id:
            default = self.get_default_price_list()
            price_list_id = default.id if default else None

        price_list = self.get_price_list(price_list_id) if price_list_id else None

        # Get unit price
        if procedure_id:
            unit_price = self.get_procedure_price(procedure_id, price_list_id)
        else:
            unit_price = treatment.cost  # Use existing cost

        # Update treatment
        treatment.price_list_id = price_list_id
        treatment.unit_price = unit_price

        # Create snapshot
        snapshot = {
            "list_id": price_list_id,
            "list_name": price_list.name if price_list else "كاش",
            "list_type": price_list.type if price_list else "cash",
            "unit_price": unit_price,
            "discount": treatment.discount,
            "snapshot_date": date.today().isoformat(),
        }
        treatment.price_snapshot = json.dumps(snapshot, ensure_ascii=False)

        # Calculate final cost
        if treatment.discount:
            treatment.cost = unit_price - treatment.discount
        else:
            treatment.cost = unit_price

        return treatment

    # --- Insurance Calculations ---

    def calculate_patient_share(
        self, total: float, price_list: PriceList
    ) -> Dict[str, float]:
        """
        Calculate patient vs insurance share.

        Returns:
            {
                "total": 500,
                "insurance_pays": 400,
                "patient_pays": 100,
                "copay_type": "percent" | "fixed"
            }
        """
        if price_list.type != "insurance":
            return {
                "total": total,
                "insurance_pays": 0.0,
                "patient_pays": total,
                "copay_type": "none",
            }

        # Calculate based on coverage
        coverage_amount = total * (price_list.coverage_percent / 100)

        # Apply copay
        if price_list.copay_fixed > 0:
            patient_pays = price_list.copay_fixed
            copay_type = "fixed"
        else:
            patient_pays = total * (price_list.copay_percent / 100)
            copay_type = "percent"

        insurance_pays = total - patient_pays

        return {
            "total": total,
            "insurance_pays": max(0, insurance_pays),
            "patient_pays": max(0, patient_pays),
            "copay_type": copay_type,
        }


def get_pricing_service(db: Session, tenant_id: int) -> PricingService:
    """Factory function for pricing service."""
    return PricingService(db, tenant_id)
