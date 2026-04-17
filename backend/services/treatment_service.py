"""
Treatment Service

Central service for all treatment-related operations:
- Create/update treatments with pricing and stock logic
- Stock validation and consumption
- Price snapshot creation

This removes business logic from the treatments router.
"""

import json
import logging
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend import models, schemas
from backend.services.pricing_service import get_pricing_service
from backend.services.inventory_service import inventory_service
from backend.utils.audit_logger import log_admin_action

logger = logging.getLogger(__name__)


class TreatmentService:
    """Central treatment logic - SINGLE SOURCE OF TRUTH."""

    def __init__(self, db: Session, tenant_id: int, current_user: models.User):
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user
        self.pricing = get_pricing_service(db, tenant_id)

    # --- Pricing & Snapshot ---

    def _calculate_price_and_snapshot(
        self,
        treatment_data: schemas.TreatmentCreate,
        price_list_id: Optional[int],
    ) -> tuple[float, Optional[str]]:
        """
        Calculate unit price and create price snapshot.

        Returns:
            (unit_price, price_snapshot_json)
        """
        # Get patient's default price list if not provided
        if not price_list_id:
            patient = (
                self.db.query(models.Patient)
                .filter(
                    models.Patient.id == treatment_data.patient_id,
                    models.Patient.tenant_id == self.tenant_id,
                )
                .first()
            )
            price_list_id = patient.default_price_list_id if patient else None

        # Find procedure
        procedure = (
            self.db.query(models.Procedure)
            .filter(
                models.Procedure.name == treatment_data.procedure,
                or_(
                    models.Procedure.tenant_id == self.tenant_id,
                    models.Procedure.tenant_id.is_(None),
                ),
            )
            .first()
        )

        unit_price = 0.0
        price_snapshot = None

        if procedure:
            unit_price = self.pricing.get_procedure_price(procedure.id, price_list_id)

            # Create price snapshot
            price_list = self.pricing.get_price_list(price_list_id)
            snapshot = {
                "list_id": price_list_id,
                "list_name": price_list.name if price_list else "Standard",
                "unit_price": unit_price,
                "date": date.today().isoformat(),
            }
            price_snapshot = json.dumps(snapshot)

        return unit_price, price_snapshot

    # --- Stock Operations ---

    def validate_treatment_stock(
        self, consumed_materials: List[schemas.clinical.ConsumedMaterialItem]
    ) -> None:
        """
        Validate stock availability for all materials.

        Raises HTTPException with detailed message if insufficient stock.
        """
        from fastapi import HTTPException

        if not consumed_materials:
            return

        errors = []
        for item in consumed_materials:
            try:
                is_valid, available, mat_name = inventory_service.validate_stock(
                    material_id=item.material_id,
                    quantity=item.quantity,
                    tenant_id=self.tenant_id,
                    db=self.db,
                )
                if not is_valid:
                    errors.append(
                        f"{mat_name} (Need: {item.quantity}, Available: {available})"
                    )
            except Exception as e:
                logger.error(f"Stock Validation Error for material {item.material_id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500, detail=f"Stock Validation Error: {str(e)}"
                )

        if errors:
            raise HTTPException(
                status_code=400,
                detail="فشل حفظ العلاج بسبب نقص المخزون: " + " | ".join(errors),
            )

    def consume_treatment_stock(
        self,
        treatment_id: int,
        consumed_materials: List[schemas.clinical.ConsumedMaterialItem],
    ) -> None:
        """
        Consume stock for treatment materials.

        Raises HTTPException (409 for CONFIRM_OPEN_REQUIRED, 500 for other errors).
        """
        from fastapi import HTTPException

        if not consumed_materials:
            return

        for item in consumed_materials:
            try:
                inventory_service.consume_stock(
                    material_id=item.material_id,
                    quantity=item.quantity,
                    tenant_id=self.tenant_id,
                    user_id=self.current_user.id,
                    reference_id=f"TREATMENT:{treatment_id}",
                    db=self.db,
                )
            except Exception as e:
                logger.error(f"Stock Consumption Error: {e}", exc_info=True)
                error_msg = str(e)

                # Handle CONFIRM_OPEN_REQUIRED as business logic error (409)
                if error_msg.startswith("CONFIRM_OPEN_REQUIRED:"):
                    parts = error_msg.split(":", 2)
                    stock_item_id = int(parts[1]) if len(parts) > 1 else None
                    material_info = parts[2] if len(parts) > 2 else "Unknown"
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "CONFIRM_OPEN_REQUIRED",
                            "stock_item_id": stock_item_id,
                            "material_info": material_info,
                            "message": f"يجب فتح عبوة جديدة قبل الاستخدام: {material_info}",
                        },
                    )

                raise HTTPException(status_code=500, detail=f"Stock Error: {error_msg}")

    # --- Treatment CRUD ---

    def create_treatment(
        self,
        treatment_data: schemas.TreatmentCreate,
    ) -> models.Treatment:
        """
        Create treatment with pricing, stock validation, and consumption.

        Flow:
        1. Validate patient exists
        2. Validate stock (pre-check)
        3. Calculate pricing + snapshot
        4. Create treatment (deferred commit)
        5. Consume stock (post-creation)
        6. Commit transaction
        7. Log admin action
        """
        from fastapi import HTTPException
        from backend import crud

        # 1. Verify patient exists
        patient = crud.get_patient(self.db, treatment_data.patient_id, self.tenant_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # 2. Validate stock (pre-check)
        self.validate_treatment_stock(treatment_data.consumedMaterials or [])

        # 3. Calculate price and snapshot
        price_list_id = getattr(treatment_data, "price_list_id", None)
        unit_price, price_snapshot = self._calculate_price_and_snapshot(
            treatment_data, price_list_id
        )

        # 4. Auto-assign doctor if not provided
        doctor_id = treatment_data.doctor_id if treatment_data.doctor_id else self.current_user.id

        # 5. Create treatment (deferred commit)
        created_treatment = crud.create_treatment(
            db=self.db,
            treatment=treatment_data,
            tenant_id=self.tenant_id,
            doctor_id=doctor_id,
            price_list_id=price_list_id,
            unit_price=unit_price,
            price_snapshot=price_snapshot,
            commit=False,
        )

        # 6. Consume stock (post-creation)
        self.consume_treatment_stock(created_treatment.id, treatment_data.consumedMaterials or [])

        # 7. Commit transaction
        self.db.commit()
        self.db.refresh(created_treatment)

        # 8. Log admin action
        log_admin_action(
            db=self.db,
            admin_user=self.current_user,
            action="create",
            entity_type="treatment",
            entity_id=created_treatment.id,
            details=f"Treatment '{treatment_data.procedure}' for patient {treatment_data.patient_id}",
        )

        return created_treatment

    def update_treatment(
        self,
        treatment_id: int,
        treatment_data: schemas.TreatmentCreate,
    ) -> models.Treatment:
        """
        Update treatment with stock validation and consumption.

        Flow:
        1. Validate stock (pre-check)
        2. Update treatment (deferred commit)
        3. Consume stock (post-update)
        4. Commit transaction
        """
        from backend import crud

        # 1. Validate stock (pre-check)
        self.validate_treatment_stock(treatment_data.consumedMaterials or [])

        # 2. Update treatment (deferred commit)
        updated_treatment = crud.update_treatment(
            self.db, treatment_id, treatment_data, self.tenant_id, commit=False
        )

        # 3. Consume stock (post-update)
        self.consume_treatment_stock(treatment_id, treatment_data.consumedMaterials or [])

        # 4. Commit transaction
        self.db.commit()
        self.db.refresh(updated_treatment)

        return updated_treatment

    def delete_treatment(self, treatment_id: int) -> dict:
        """Delete a treatment record."""
        from backend import crud

        log_admin_action(
            db=self.db,
            admin_user=self.current_user,
            action="delete",
            entity_type="treatment",
            entity_id=treatment_id,
            details=f"Deleted treatment #{treatment_id}",
        )
        return crud.delete_treatment(self.db, treatment_id, self.tenant_id)


# Factory function
def get_treatment_service(db: Session, tenant_id: int, current_user: models.User) -> TreatmentService:
    """Factory function for treatment service."""
    return TreatmentService(db, tenant_id, current_user)
