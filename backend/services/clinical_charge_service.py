"""
Clinical Charge Service (Slice S33).

Manages pending clinical charges derived from completed native clinical work items (D1).
Provides:
- Pending charge creation on native completion (D1-D4, D6).
- Optimistic version checking and state transitions for reception invoicing/voiding (D5).
- Work item billing projection (G14-M03).
- Strict fail-closed feature flag gates for read and native writes (D7).
"""

from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from backend import models
from backend.models.clinical_core import (
    CLINICAL_CHARGE_STATUS_INVOICED,
    CLINICAL_CHARGE_STATUS_PENDING,
    CLINICAL_CHARGE_STATUS_VOIDED,
)
from backend.services.feature_service import FeatureFlagService
from backend.services.treatment_plan_service import TreatmentPlanService
from backend.utils.audit_logger import log_admin_action

logger = logging.getLogger(__name__)

FEATURE_FLAG_CLINICAL_NATIVE_WRITES = "clinical_vnext_native_writes"
FEATURE_FLAG_CLINICAL_FINANCE_READ = "clinical_vnext_finance_read"


class ClinicalChargeService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        current_user: Optional[models.User] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user
        self.plan_service = TreatmentPlanService(db, tenant_id)

    async def is_native_writes_enabled(self) -> bool:
        """Check if native writes feature flag is enabled for this tenant."""
        return await FeatureFlagService.is_feature_enabled(
            self.db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, self.tenant_id
        )

    async def ensure_native_writes_enabled(self) -> None:
        """Fail-closed gate when clinical_vnext_native_writes is OFF (404)."""
        if not await self.is_native_writes_enabled():
            raise HTTPException(
                status_code=404,
                detail="Clinical native writes are disabled",
            )

    async def is_finance_read_enabled(self) -> bool:
        """Check if finance read feature flag is enabled for this tenant."""
        return await FeatureFlagService.is_feature_enabled(
            self.db, FEATURE_FLAG_CLINICAL_FINANCE_READ, self.tenant_id
        )

    async def ensure_finance_read_enabled(self) -> None:
        """Fail-closed gate when clinical_vnext_finance_read is OFF (404)."""
        if not await self.is_finance_read_enabled():
            raise HTTPException(
                status_code=404,
                detail="Clinical finance read is disabled",
            )

    async def _verify_patient(self, patient_id: int) -> models.Patient:
        """Verify patient exists and belongs to the current tenant."""
        stmt = select(models.Patient).where(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == self.tenant_id,
        )
        patient = (await self.db.execute(stmt)).scalars().first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient

    async def is_legacy_synced_work_item(self, work_item_id: int) -> bool:
        """
        Check if a work item was created from / synced with a legacy Treatment.
        Inspects ClinicalEvents for payload containing treatment_id or legacy_treatment_id.
        """
        stmt = select(models.ClinicalEvent.payload).where(
            models.ClinicalEvent.tenant_id == self.tenant_id,
            models.ClinicalEvent.work_item_id == work_item_id,
        )
        payloads = (await self.db.execute(stmt)).scalars().all()
        for p in payloads:
            if isinstance(p, dict):
                if p.get("treatment_id") is not None or p.get("legacy_treatment_id") is not None:
                    return True
        return False

    async def create_pending_for_work_item(
        self,
        work_item_id: int,
        doctor_id: Optional[int] = None,
        care_session_id: Optional[int] = None,
    ) -> Optional[models.ClinicalCharge]:
        """
        Create a pending clinical charge row for a completed native procedure (D1-D4, D6).
        Idempotent: if a non-voided charge exists, does nothing.
        Tolerates concurrent inserts via savepoint + IntegrityError.
        Never blocks clinical completion (D6): runs inside a savepoint, logs error and returns None on failure.
        """
        # Gated by clinical_vnext_native_writes (D7)
        if not await self.is_native_writes_enabled():
            return None

        # Load work item
        stmt_wi = select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.id == work_item_id,
            models.ClinicalWorkItem.tenant_id == self.tenant_id,
        )
        work_item = (await self.db.execute(stmt_wi)).scalars().first()
        if not work_item:
            return None

        # D2: Only kind == "procedure" work items produce charges
        if work_item.kind != "procedure":
            return None

        # D4: Legacy-synced work items get no charge row
        if await self.is_legacy_synced_work_item(work_item.id):
            return None

        # Idempotency check: if an active (non-voided) charge already exists, do nothing
        stmt_existing = select(models.ClinicalCharge).where(
            models.ClinicalCharge.tenant_id == self.tenant_id,
            models.ClinicalCharge.work_item_id == work_item.id,
            models.ClinicalCharge.status != CLINICAL_CHARGE_STATUS_VOIDED,
        )
        existing_charge = (await self.db.execute(stmt_existing)).scalars().first()
        if existing_charge:
            return existing_charge

        # D3: Resolve amount using existing estimate logic
        amount = await self.plan_service.resolve_procedure_price(
            work_item.patient_id, work_item.code
        )
        if amount is None or amount <= Decimal("0.00"):
            # D3: If no price resolves: create no row, emit a structured warning log
            logger.warning(
                "clinical_charge_skipped_unresolved_price work_item_id=%s tenant_id=%s code=%s",
                work_item.id,
                self.tenant_id,
                work_item.code,
                extra={
                    "work_item_id": work_item.id,
                    "tenant_id": self.tenant_id,
                    "code": work_item.code,
                },
            )
            return None

        # D6: Non-blocking creation inside a savepoint
        effective_doctor_id = doctor_id or work_item.created_by_user_id
        try:
            async with self.db.begin_nested():
                charge = models.ClinicalCharge(
                    tenant_id=self.tenant_id,
                    patient_id=work_item.patient_id,
                    work_item_id=work_item.id,
                    care_session_id=care_session_id,
                    doctor_id=effective_doctor_id,
                    amount=amount,
                    discount=Decimal("0.00"),
                    status=CLINICAL_CHARGE_STATUS_PENDING,
                    version_id=1,
                )
                self.db.add(charge)
                await self.db.flush()
                return charge
        except IntegrityError as exc:
            # Idempotent tolerance of concurrent insert (e.g. uq_cc_active_work_item)
            logger.warning(
                "clinical_charge_insert_conflict work_item_id=%s tenant_id=%s: %s",
                work_item.id,
                self.tenant_id,
                exc,
                extra={"work_item_id": work_item.id, "tenant_id": self.tenant_id},
            )
            # Fetch existing non-voided charge
            stmt_reload = select(models.ClinicalCharge).where(
                models.ClinicalCharge.tenant_id == self.tenant_id,
                models.ClinicalCharge.work_item_id == work_item.id,
                models.ClinicalCharge.status != CLINICAL_CHARGE_STATUS_VOIDED,
            )
            return (await self.db.execute(stmt_reload)).scalars().first()
        except Exception as exc:
            # D6: Charge creation never blocks clinical completion
            logger.error(
                "clinical_charge_creation_failed work_item_id=%s tenant_id=%s: %s",
                work_item.id,
                self.tenant_id,
                exc,
                exc_info=True,
                extra={"work_item_id": work_item.id, "tenant_id": self.tenant_id},
            )
            return None

    async def get_work_item_billing_projection(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Project billing information for all work items belonging to patient_id (G14-M03).
        Per work item:
        - source: 'clinical_charge' | 'legacy_treatment' | 'none'
        - amount: float or None
        - discount: float or None
        - status: charge.status | treatment.status | None
        - charge_id: int or None
        - treatment_id: int or None
        """
        # 1. Fetch work items for patient
        stmt_wi = (
            select(models.ClinicalWorkItem)
            .where(
                models.ClinicalWorkItem.patient_id == patient_id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
            .order_by(models.ClinicalWorkItem.id.asc())
        )
        work_items = (await self.db.execute(stmt_wi)).scalars().all()
        if not work_items:
            return []

        wi_ids = [w.id for w in work_items]

        # 2. Fetch charges for patient
        stmt_charges = (
            select(models.ClinicalCharge)
            .where(
                models.ClinicalCharge.patient_id == patient_id,
                models.ClinicalCharge.tenant_id == self.tenant_id,
            )
            .order_by(models.ClinicalCharge.id.asc())
        )
        charges = (await self.db.execute(stmt_charges)).scalars().all()
        charges_by_wi: Dict[int, models.ClinicalCharge] = {}
        for c in charges:
            # Prefer non-voided charge over voided charge
            if c.work_item_id not in charges_by_wi or charges_by_wi[c.work_item_id].status == CLINICAL_CHARGE_STATUS_VOIDED:
                charges_by_wi[c.work_item_id] = c

        # 3. Fetch events for work items to find legacy treatment links
        stmt_events = (
            select(models.ClinicalEvent)
            .where(
                models.ClinicalEvent.tenant_id == self.tenant_id,
                models.ClinicalEvent.patient_id == patient_id,
                models.ClinicalEvent.work_item_id.in_(wi_ids),
            )
            .order_by(models.ClinicalEvent.id.asc())
        )
        events = (await self.db.execute(stmt_events)).scalars().all()
        wi_to_treatment_id: Dict[int, int] = {}
        for ev in events:
            if isinstance(ev.payload, dict):
                t_id = ev.payload.get("treatment_id") or ev.payload.get("legacy_treatment_id")
                if t_id is not None:
                    try:
                        wi_to_treatment_id[ev.work_item_id] = int(t_id)
                    except (ValueError, TypeError):
                        pass

        # 4. Fetch linked treatments
        treatments_by_id: Dict[int, models.Treatment] = {}
        if wi_to_treatment_id:
            stmt_tx = select(models.Treatment).where(
                models.Treatment.id.in_(list(wi_to_treatment_id.values())),
                models.Treatment.tenant_id == self.tenant_id,
            )
            tx_list = (await self.db.execute(stmt_tx)).scalars().all()
            for tx in tx_list:
                treatments_by_id[tx.id] = tx

        # 5. Build projection
        projection: List[Dict[str, Any]] = []
        for wi in work_items:
            tx_id = wi_to_treatment_id.get(wi.id)
            tx = treatments_by_id.get(tx_id) if tx_id else None
            ch = charges_by_wi.get(wi.id)

            if tx is not None:
                projection.append({
                    "work_item_id": wi.id,
                    "kind": wi.kind,
                    "code": wi.code,
                    "work_item_status": wi.status,
                    "source": "legacy_treatment",
                    "amount": float(tx.cost) if tx.cost is not None else 0.0,
                    "discount": float(tx.discount) if tx.discount is not None else 0.0,
                    "status": tx.status,
                    "charge_id": None,
                    "treatment_id": tx.id,
                })
            elif ch is not None:
                projection.append({
                    "work_item_id": wi.id,
                    "kind": wi.kind,
                    "code": wi.code,
                    "work_item_status": wi.status,
                    "source": "clinical_charge",
                    "amount": float(ch.amount) if ch.amount is not None else 0.0,
                    "discount": float(ch.discount) if ch.discount is not None else 0.0,
                    "status": ch.status,
                    "charge_id": ch.id,
                    "treatment_id": None,
                })
            else:
                projection.append({
                    "work_item_id": wi.id,
                    "kind": wi.kind,
                    "code": wi.code,
                    "work_item_status": wi.status,
                    "source": "none",
                    "amount": None,
                    "discount": None,
                    "status": None,
                    "charge_id": None,
                    "treatment_id": None,
                })

        return projection

    async def get_patient_clinical_charges(
        self, patient_id: int
    ) -> Tuple[List[models.ClinicalCharge], List[Dict[str, Any]]]:
        """
        Return patient's clinical charges and work-item billing projection.
        Fails closed (404) when clinical_vnext_finance_read is disabled.
        """
        await self.ensure_finance_read_enabled()
        await self._verify_patient(patient_id)

        stmt_charges = (
            select(models.ClinicalCharge)
            .where(
                models.ClinicalCharge.patient_id == patient_id,
                models.ClinicalCharge.tenant_id == self.tenant_id,
            )
            .order_by(models.ClinicalCharge.created_at.desc(), models.ClinicalCharge.id.desc())
        )
        charges = (await self.db.execute(stmt_charges)).scalars().all()
        projection = await self.get_work_item_billing_projection(patient_id)
        return charges, projection

    async def mark_charge_invoiced(
        self,
        charge_id: int,
        expected_version_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> models.ClinicalCharge:
        """
        Move charge status from pending -> invoiced (D5).
        Optimistic version check (409 on conflict), audited with log_admin_action.
        Fails closed (404) when clinical_vnext_native_writes is disabled.
        """
        await self.ensure_native_writes_enabled()

        stmt = select(models.ClinicalCharge).where(
            models.ClinicalCharge.id == charge_id,
            models.ClinicalCharge.tenant_id == self.tenant_id,
        )
        charge = (await self.db.execute(stmt)).scalars().first()
        if not charge:
            raise HTTPException(status_code=404, detail="Clinical charge not found")

        # Optimistic locking check
        if expected_version_id is not None and charge.version_id != expected_version_id:
            raise HTTPException(
                status_code=409,
                detail=f"Stale version: expected {expected_version_id}, found {charge.version_id}",
            )

        # State transition: only pending -> invoiced allowed
        if charge.status != CLINICAL_CHARGE_STATUS_PENDING:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot transition charge from '{charge.status}' to '{CLINICAL_CHARGE_STATUS_INVOICED}'",
            )

        # F-05: Reject invoicing charges for corrected work items
        work_item = await self.db.get(models.ClinicalWorkItem, charge.work_item_id)
        if work_item and work_item.status in ("entered_in_error", "superseded", "entered-in-error"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot invoice charge for corrected work item (status: '{work_item.status}')",
            )

        old_version = charge.version_id
        charge.status = CLINICAL_CHARGE_STATUS_INVOICED
        if notes:
            charge.notes = f"{charge.notes}\n{notes}" if charge.notes else notes

        # Audit with log_admin_action (before commit as it only calls db.add)
        log_admin_action(
            db=self.db,
            admin_user=self.current_user,
            action="invoice",
            entity_type="clinical_charge",
            entity_id=charge.id,
            tenant_id=self.tenant_id,
            details=f"Clinical charge {charge.id} marked as invoiced",
            old_value={"status": CLINICAL_CHARGE_STATUS_PENDING, "version_id": old_version},
            new_value={"status": CLINICAL_CHARGE_STATUS_INVOICED, "version_id": charge.version_id},
        )

        try:
            await self.db.commit()
            await self.db.refresh(charge)
        except StaleDataError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Concurrent modification detected on clinical charge",
            ) from exc

        return charge

    async def mark_charge_voided(
        self,
        charge_id: int,
        expected_version_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> models.ClinicalCharge:
        """
        Move charge status from pending -> voided (D5).
        Optimistic version check (409 on conflict), audited with log_admin_action.
        Fails closed (404) when clinical_vnext_native_writes is disabled.
        """
        await self.ensure_native_writes_enabled()

        stmt = select(models.ClinicalCharge).where(
            models.ClinicalCharge.id == charge_id,
            models.ClinicalCharge.tenant_id == self.tenant_id,
        )
        charge = (await self.db.execute(stmt)).scalars().first()
        if not charge:
            raise HTTPException(status_code=404, detail="Clinical charge not found")

        # Optimistic locking check
        if expected_version_id is not None and charge.version_id != expected_version_id:
            raise HTTPException(
                status_code=409,
                detail=f"Stale version: expected {expected_version_id}, found {charge.version_id}",
            )

        # State transition: only pending -> voided allowed
        if charge.status != CLINICAL_CHARGE_STATUS_PENDING:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot transition charge from '{charge.status}' to '{CLINICAL_CHARGE_STATUS_VOIDED}'",
            )

        old_version = charge.version_id
        charge.status = CLINICAL_CHARGE_STATUS_VOIDED
        if notes:
            charge.notes = f"{charge.notes}\n{notes}" if charge.notes else notes

        # Audit with log_admin_action (before commit as it only calls db.add)
        log_admin_action(
            db=self.db,
            admin_user=self.current_user,
            action="void",
            entity_type="clinical_charge",
            entity_id=charge.id,
            tenant_id=self.tenant_id,
            details=f"Clinical charge {charge.id} marked as voided",
            old_value={"status": CLINICAL_CHARGE_STATUS_PENDING, "version_id": old_version},
            new_value={"status": CLINICAL_CHARGE_STATUS_VOIDED, "version_id": charge.version_id},
        )

        try:
            await self.db.commit()
            await self.db.refresh(charge)
        except StaleDataError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Concurrent modification detected on clinical charge",
            ) from exc

        return charge
