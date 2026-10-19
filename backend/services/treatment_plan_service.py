"""
Clinical Treatment Plan Service (Slices G9a, G9b, G9c, S12, S13, S15).

Manages patient-level treatment plans with sequential phases, procedure membership,
and dynamic fee estimate projections.

Enforces:
- Tenant isolation and patient visibility scoping (404 on mismatch).
- Feature flag gate (fail-closed 404 when disabled).
- Single default phase ("Phase 1", phase_order 0, draft) on plan creation.
- Creator attribution (created_by_user_id).
- Phase creation with sequential phase_order and retry on ordering race.
- Procedure/work-item attachment with non-cancelled validation and 409 duplicate check.
- Work items shared across alternative plans without duplicating care episodes (G9-M05).
- Unlink item leaves underlying ClinicalWorkItem untouched.
- Legacy Non-Interference Safety Invariants (G9-M12):
  1. Zero side effects on legacy tables:
     Creating, editing, reordering, estimating, proposing, accepting, completing, or
     cancelling plans strictly mutates native clinical plan tables and NEVER writes to,
     updates, or deletes rows in:
     - `treatments` (models.Treatment)
     - `treatment_sessions` (models.TreatmentSession)
     - `payments` (models.Payment)
     - `stock_movements` (models.StockMovement)
     - `treatment_material_usages` (models.TreatmentMaterialUsage)
     - `lab_orders` (models.LabOrder)
  2. Zero procedure duplication across alternative plans:
     Procedures shared across alternative plans (Plan A vs. Plan B) link via independent
     `ClinicalTreatmentPlanItem` references, keeping `ClinicalWorkItem` row count constant.
  3. Zero impact on patient billing balances:
     Legacy billing queries and `BillingService.get_outstanding_balance(patient_id)`
     remain 100% invariant across all treatment plan operations.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple, Union
from fastapi import HTTPException
from sqlalchemy import func, inspect, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.core.config import is_clinical_treatment_plans_enabled
from backend.services.feature_service import FeatureFlagService
from backend.services.patient_access_service import ensure_patient_visible
from backend.utils.audit_logger import log_admin_action

FEATURE_KEY_TREATMENT_PLANS = "clinical_treatment_plans"

ALLOWED_PLAN_TRANSITIONS = {
    "draft": {"proposed", "cancelled"},
    "proposed": {"accepted", "cancelled"},
    "accepted": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _eager_plan_options():
    return (
        selectinload(models.ClinicalTreatmentPlan.phases)
        .selectinload(models.ClinicalTreatmentPlanPhase.items)
        .selectinload(models.ClinicalTreatmentPlanItem.work_item)
        .selectinload(models.ClinicalWorkItem.targets)
    )


# The product has no per-tenant currency yet (Tenant has no currency column; the finance UI is EGP-only).
# Keep a single named constant so a future multi-currency change has one place to update.
ESTIMATE_CURRENCY = "EGP"


class TreatmentPlanService:
    # Models strictly forbidden from being written to by TreatmentPlanService (G9-M12)
    LEGACY_FORBIDDEN_WRITE_MODELS: Tuple[type, ...] = (
        models.Treatment,
        models.TreatmentSession,
        models.Payment,
        models.StockMovement,
        models.TreatmentMaterialUsage,
        models.LabOrder,
    )
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        current_user: Optional[models.User] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user
        self.current_user_id = getattr(current_user, "id", None)

    async def _get_active_current_user(self) -> Optional[models.User]:
        if not self.current_user or not self.current_user_id:
            return self.current_user
        state = inspect(self.current_user, raiseerr=False)
        if state and (state.expired or state.detached or bool(state.expired_attributes)):
            stmt = select(models.User).where(
                models.User.id == self.current_user_id,
                models.User.tenant_id == self.tenant_id,
            )
            reloaded = (await self.db.execute(stmt)).scalar_one_or_none()
            if reloaded:
                self.current_user = reloaded
        return self.current_user

    async def is_enabled(self) -> bool:
        """
        Check if treatment plans are enabled.
        Priority:
        1. Config flag / environment variable override.
        2. Per-tenant feature flag mechanism via FeatureFlagService.
        """
        if is_clinical_treatment_plans_enabled():
            return True
        if self.tenant_id:
            return await FeatureFlagService.is_feature_enabled(
                self.db, FEATURE_KEY_TREATMENT_PLANS, self.tenant_id
            )
        return False

    async def ensure_enabled(self) -> None:
        """Enforce server-side 404 when disabled."""
        if not await self.is_enabled():
            raise HTTPException(
                status_code=404,
                detail="Treatment plans feature is disabled",
            )

    async def _verify_patient(self, patient_id: int) -> None:
        """Validate patient exists within tenant and is visible to current user."""
        user = await self._get_active_current_user()
        if user:
            await ensure_patient_visible(self.db, user, patient_id)
        else:
            stmt = select(models.Patient).where(
                models.Patient.id == patient_id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            patient = (await self.db.execute(stmt)).scalar_one_or_none()
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")

    async def _get_plan_and_verify(
        self, patient_id: int, plan_id: int
    ) -> models.ClinicalTreatmentPlan:
        """Validate plan exists, belongs to tenant and patient."""
        await self.ensure_enabled()
        await self._verify_patient(patient_id)

        stmt = select(models.ClinicalTreatmentPlan).where(
            models.ClinicalTreatmentPlan.id == plan_id,
            models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
            models.ClinicalTreatmentPlan.patient_id == patient_id,
        )
        plan = (await self.db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Treatment plan not found")
        return plan

    async def _get_phase_and_verify(
        self, patient_id: int, plan_id: int, phase_id: int
    ) -> Tuple[models.ClinicalTreatmentPlan, models.ClinicalTreatmentPlanPhase]:
        """Validate plan and phase exist and belong together within tenant/patient."""
        plan = await self._get_plan_and_verify(patient_id, plan_id)

        stmt = select(models.ClinicalTreatmentPlanPhase).where(
            models.ClinicalTreatmentPlanPhase.id == phase_id,
            models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
            models.ClinicalTreatmentPlanPhase.plan_id == plan.id,
        )
        phase = (await self.db.execute(stmt)).scalar_one_or_none()
        if not phase:
            raise HTTPException(status_code=404, detail="Treatment plan phase not found")
        return plan, phase

    async def _attach_dynamic_estimates(
        self,
        patient_id: int,
        plans: Union[models.ClinicalTreatmentPlan, List[models.ClinicalTreatmentPlan]],
    ) -> None:
        """
        Dynamically calculate and attach on-the-fly fee estimates per item, phase, and plan (Decision D2 & PD04).
        Zero database writes: Never modifies database or creates treatment/payment/charge rows.
        Resolution Order per procedure (PD04):
        1. Patient default price list (PriceListItem)
        2. Clinic default price list (PriceListItem)
        3. Procedure base price (Procedure.price)
        4. If not found or procedure unpriced, fee=0.00 and unpriced=True.

        Money is accumulated with ``Decimal`` (quantized to 0.01, half-up) and only converted
        to ``float`` at the API boundary, so phase/plan totals never drift. Only the procedures
        and price rows that the plans' work-item codes can actually match are loaded.

        Also attaches ``estimate_price_list_id`` (patient price list when set, otherwise the
        clinic default list) to every plan so the estimate endpoint reports the list in effect.
        """
        if not plans:
            return

        plan_list = plans if isinstance(plans, list) else [plans]

        # 1. Look up patient's default_price_list_id
        stmt_patient = select(models.Patient.default_price_list_id).where(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == self.tenant_id,
        )
        patient_price_list_id = (await self.db.execute(stmt_patient)).scalar_one_or_none()

        # 2. Look up clinic default price list
        stmt_def_list = select(models.PriceList).where(
            models.PriceList.tenant_id == self.tenant_id,
            models.PriceList.is_default == True,
            models.PriceList.is_active == True,
        )
        def_list = (await self.db.execute(stmt_def_list)).scalars().first()
        clinic_default_price_list_id = def_list.id if def_list else None

        # 3. Collect the distinct work-item codes referenced by these plans
        def _clean_code(item: Any) -> str:
            work_item = getattr(item, "work_item", None)
            code = getattr(work_item, "code", "") if work_item else ""
            return str(code).strip() if code else ""

        codes: set = set()
        for plan in plan_list:
            for phase in getattr(plan, "phases", []) or []:
                for item in getattr(phase, "items", []) or []:
                    clean = _clean_code(item)
                    if clean:
                        codes.add(clean)

        from backend.clinical.legacy_mapping import LEGACY_PROCEDURE_ALLOWLIST

        # 4. Load only procedures that can match one of those codes (this tenant + globals).
        #    (Procedure.name is globally unique, so a code maps to at most one procedure.)
        proc_by_key: Dict[str, models.Procedure] = {}
        if codes:
            lowered_codes = {c.lower() for c in codes}
            legacy_names = [name for name, canon in LEGACY_PROCEDURE_ALLOWLIST.items() if canon in codes]
            name_filters = [func.lower(func.trim(models.Procedure.name)).in_(lowered_codes)]
            if legacy_names:
                name_filters.append(func.trim(models.Procedure.name).in_(legacy_names))
            stmt_procs = (
                select(models.Procedure)
                .where(
                    or_(
                        models.Procedure.tenant_id == self.tenant_id,
                        models.Procedure.tenant_id.is_(None),
                    ),
                    or_(*name_filters),
                )
                .order_by(models.Procedure.id)
            )
            procs = (await self.db.execute(stmt_procs)).scalars().all()

            for p in procs:
                if not p.name:
                    continue
                name_clean = p.name.strip()
                proc_by_key[name_clean] = p
                proc_by_key[name_clean.lower()] = p
                if name_clean in LEGACY_PROCEDURE_ALLOWLIST:
                    canon = LEGACY_PROCEDURE_ALLOWLIST[name_clean]
                    if canon not in proc_by_key:
                        proc_by_key[canon] = p
                        proc_by_key[canon.lower()] = p

        matched_proc_ids = {p.id for p in proc_by_key.values()}

        # 5. Load price list items only for matched procedures
        patient_prices: Dict[int, Decimal] = {}
        clinic_default_prices: Dict[int, Decimal] = {}
        if matched_proc_ids:
            if patient_price_list_id:
                stmt_pli = select(models.PriceListItem).where(
                    models.PriceListItem.price_list_id == patient_price_list_id,
                    models.PriceListItem.procedure_id.in_(matched_proc_ids),
                )
                for pli in (await self.db.execute(stmt_pli)).scalars().all():
                    if pli.final_price is not None:
                        patient_prices[pli.procedure_id] = Decimal(str(pli.final_price))

            if clinic_default_price_list_id and clinic_default_price_list_id != patient_price_list_id:
                stmt_def_pli = select(models.PriceListItem).where(
                    models.PriceListItem.price_list_id == clinic_default_price_list_id,
                    models.PriceListItem.procedure_id.in_(matched_proc_ids),
                )
                for pli in (await self.db.execute(stmt_def_pli)).scalars().all():
                    if pli.final_price is not None:
                        clinic_default_prices[pli.procedure_id] = Decimal(str(pli.final_price))

        cent = Decimal("0.01")
        zero = Decimal("0.00")

        # 6. Calculate and attach estimates
        for plan in plan_list:
            plan_total = zero
            plan_unpriced_count = 0

            for phase in getattr(plan, "phases", []) or []:
                phase_total = zero
                phase_unpriced_count = 0

                for item in getattr(phase, "items", []) or []:
                    clean_code = _clean_code(item)

                    # Find matching Procedure
                    matching_proc = (
                        proc_by_key.get(clean_code)
                        or proc_by_key.get(clean_code.lower())
                    )

                    fee = zero
                    is_unpriced = True

                    if matching_proc:
                        # Priority 1: Patient default price list
                        if matching_proc.id in patient_prices:
                            fee = patient_prices[matching_proc.id]
                            is_unpriced = False
                        # Priority 2: Clinic default price list
                        elif matching_proc.id in clinic_default_prices:
                            fee = clinic_default_prices[matching_proc.id]
                            is_unpriced = False
                        # Priority 3: Base Procedure price
                        elif matching_proc.price is not None:
                            fee = Decimal(str(matching_proc.price))
                            is_unpriced = False

                    fee = fee.quantize(cent, rounding=ROUND_HALF_UP)
                    item.estimated_fee = float(fee)
                    item.unpriced = is_unpriced

                    phase_total += fee
                    if is_unpriced:
                        phase_unpriced_count += 1

                phase.phase_estimated_total = float(phase_total)
                phase.unpriced_items_count = phase_unpriced_count

                plan_total += phase_total
                plan_unpriced_count += phase_unpriced_count

            plan.plan_estimated_total = float(plan_total)
            plan.unpriced_items_count = plan_unpriced_count
            plan.estimate_price_list_id = patient_price_list_id or clinic_default_price_list_id

    async def get_plan(
        self,
        patient_id: int,
        plan_id: int,
    ) -> models.ClinicalTreatmentPlan:
        """Get single treatment plan with dynamic fee estimates attached."""
        await self.ensure_enabled()
        await self._verify_patient(patient_id)

        stmt = (
            select(models.ClinicalTreatmentPlan)
            .where(
                models.ClinicalTreatmentPlan.id == plan_id,
                models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
                models.ClinicalTreatmentPlan.patient_id == patient_id,
            )
            .options(_eager_plan_options())
            .execution_options(populate_existing=True)
        )
        plan = (await self.db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Treatment plan not found")
        await self._attach_dynamic_estimates(patient_id, plan)
        return plan

    async def get_plan_estimate(
        self,
        patient_id: int,
        plan_id: int,
    ) -> schemas.ClinicalTreatmentPlanEstimateRead:
        """Project dynamic on-the-fly fee estimate for a treatment plan (G9-M10)."""
        await self.ensure_enabled()
        await self._verify_patient(patient_id)

        plan = await self.get_plan(patient_id, plan_id)

        phase_estimates = [
            schemas.ClinicalTreatmentPlanPhaseEstimateRead(
                phase_id=ph.id,
                phase_order=ph.phase_order,
                phase_name=ph.name,
                phase_estimated_total=getattr(ph, "phase_estimated_total", 0.0),
                unpriced_items_count=getattr(ph, "unpriced_items_count", 0),
                items=[schemas.ClinicalTreatmentPlanItemRead.model_validate(it) for it in ph.items],
            )
            for ph in sorted(plan.phases or [], key=lambda p: p.phase_order)
        ]

        return schemas.ClinicalTreatmentPlanEstimateRead(
            plan_id=plan.id,
            patient_id=plan.patient_id,
            plan_title=plan.title,
            plan_status=plan.status,
            plan_estimated_total=getattr(plan, "plan_estimated_total", 0.0),
            unpriced_items_count=getattr(plan, "unpriced_items_count", 0),
            currency=ESTIMATE_CURRENCY,
            price_list_id=getattr(plan, "estimate_price_list_id", None),
            phases=phase_estimates,
        )

    async def create_plan(
        self,
        patient_id: int,
        plan_data: schemas.ClinicalTreatmentPlanCreate,
    ) -> models.ClinicalTreatmentPlan:
        await self.ensure_enabled()
        await self._verify_patient(patient_id)

        clean_title = plan_data.title.strip()
        if not clean_title:
            raise HTTPException(status_code=422, detail="Title cannot be empty")

        clean_notes = plan_data.notes.strip() if plan_data.notes else None

        # 1. Create plan
        plan = models.ClinicalTreatmentPlan(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            title=clean_title,
            status="draft",
            notes=clean_notes,
            created_by_user_id=self.current_user_id,
        )
        self.db.add(plan)
        await self.db.flush()

        # 2. Decision 2: Creating a plan also creates ONE default phase (phase_order 0, localized "Phase 1")
        default_phase = models.ClinicalTreatmentPlanPhase(
            tenant_id=self.tenant_id,
            plan_id=plan.id,
            phase_order=0,
            name="Phase 1",
            status="draft",
            notes=None,
        )
        self.db.add(default_phase)
        await self.db.commit()

        # 3. Reload with eager phases and items
        stmt = (
            select(models.ClinicalTreatmentPlan)
            .where(
                models.ClinicalTreatmentPlan.id == plan.id,
                models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
            )
            .options(_eager_plan_options())
        )
        reloaded_plan = (await self.db.execute(stmt)).scalar_one()
        await self._attach_dynamic_estimates(patient_id, reloaded_plan)
        return reloaded_plan

    async def list_plans(
        self,
        patient_id: int,
    ) -> List[models.ClinicalTreatmentPlan]:
        await self.ensure_enabled()
        await self._verify_patient(patient_id)

        stmt = (
            select(models.ClinicalTreatmentPlan)
            .where(
                models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
                models.ClinicalTreatmentPlan.patient_id == patient_id,
            )
            .options(_eager_plan_options())
            .execution_options(populate_existing=True)
            .order_by(
                models.ClinicalTreatmentPlan.created_at.desc(),
                models.ClinicalTreatmentPlan.id.desc(),
            )
        )
        res = await self.db.execute(stmt)
        plans = list(res.scalars().all())
        await self._attach_dynamic_estimates(patient_id, plans)
        return plans

    async def get_candidate_work_items(
        self,
        patient_id: int,
        plan_id: int,
    ) -> List[models.ClinicalWorkItem]:
        """
        Amendment A: Return patient's non-cancelled ClinicalWorkItems for selector.
        Tenant and patient scoped.
        """
        await self._get_plan_and_verify(patient_id, plan_id)

        stmt = (
            select(models.ClinicalWorkItem)
            .where(
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
                models.ClinicalWorkItem.kind == "procedure",
                models.ClinicalWorkItem.status != "cancelled",
            )
            .options(selectinload(models.ClinicalWorkItem.targets))
            .order_by(
                models.ClinicalWorkItem.created_at.desc(),
                models.ClinicalWorkItem.id.desc(),
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def add_phase(
        self,
        patient_id: int,
        plan_id: int,
        data: schemas.ClinicalTreatmentPlanPhaseCreate,
    ) -> models.ClinicalTreatmentPlanPhase:
        """
        Add a new phase to the plan.
        Allowed only in 'draft' or 'proposed' status (Decision 4).
        Auto-assigns next phase_order, validates name, retries on ordering race without expired-attribute errors.
        """
        plan = await self._get_plan_and_verify(patient_id, plan_id)
        if plan.status not in ("draft", "proposed"):
            raise HTTPException(
                status_code=409,
                detail=f"Phases cannot be added to a plan in '{plan.status}' status",
            )

        plan_id_val = plan.id
        clean_name = data.name.strip()
        if not clean_name:
            raise HTTPException(status_code=422, detail="Phase name cannot be empty")
        if len(clean_name) > 255:
            raise HTTPException(status_code=422, detail="Phase name cannot exceed 255 characters")
        clean_notes = data.notes.strip() if data.notes else None

        async def _attempt_insert() -> models.ClinicalTreatmentPlanPhase:
            max_order_stmt = select(func.max(models.ClinicalTreatmentPlanPhase.phase_order)).where(
                models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
                models.ClinicalTreatmentPlanPhase.plan_id == plan_id_val,
            )
            max_order = (await self.db.execute(max_order_stmt)).scalar()
            next_order = (max_order + 1) if max_order is not None else 0

            phase = models.ClinicalTreatmentPlanPhase(
                tenant_id=self.tenant_id,
                plan_id=plan_id_val,
                phase_order=next_order,
                name=clean_name,
                status="draft",
                notes=clean_notes,
            )
            self.db.add(phase)
            await self.db.flush()
            saved_phase_id = phase.id
            await self.db.commit()

            stmt_reload = (
                select(models.ClinicalTreatmentPlanPhase)
                .where(
                    models.ClinicalTreatmentPlanPhase.id == saved_phase_id,
                    models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
                )
                .options(
                    selectinload(models.ClinicalTreatmentPlanPhase.items)
                    .selectinload(models.ClinicalTreatmentPlanItem.work_item)
                    .selectinload(models.ClinicalWorkItem.targets)
                )
                .execution_options(populate_existing=True)
            )
            phase_obj = (await self.db.execute(stmt_reload)).scalar_one_or_none() or phase
            phase_obj.phase_estimated_total = 0.0
            phase_obj.unpriced_items_count = 0
            return phase_obj

        try:
            return await _attempt_insert()
        except IntegrityError:
            await self.db.rollback()
            try:
                return await _attempt_insert()
            except IntegrityError:
                await self.db.rollback()
                raise HTTPException(status_code=409, detail="Concurrent phase order conflict")

    async def update_phase(
        self,
        patient_id: int,
        plan_id: int,
        phase_id: int,
        data: schemas.ClinicalTreatmentPlanPhaseUpdate,
    ) -> models.ClinicalTreatmentPlanPhase:
        """
        Update phase name or notes.
        Allowed only in 'draft' or 'proposed' plan status (G9-M03).
        """
        plan, phase = await self._get_phase_and_verify(patient_id, plan_id, phase_id)
        if plan.status not in ("draft", "proposed"):
            raise HTTPException(
                status_code=409,
                detail=f"Phases cannot be updated in a plan in '{plan.status}' status",
            )

        if data.name is not None:
            clean_name = data.name.strip()
            if not clean_name:
                raise HTTPException(status_code=422, detail="Phase name cannot be empty")
            if len(clean_name) > 255:
                raise HTTPException(status_code=422, detail="Phase name cannot exceed 255 characters")
            phase.name = clean_name

        if data.notes is not None:
            phase.notes = data.notes.strip() if data.notes.strip() else None

        try:
            await self.db.commit()
        except (IntegrityError, StaleDataError):
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Phase was modified concurrently by another user",
            )

        stmt = (
            select(models.ClinicalTreatmentPlanPhase)
            .where(
                models.ClinicalTreatmentPlanPhase.id == phase.id,
                models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
            )
            .options(
                selectinload(models.ClinicalTreatmentPlanPhase.items)
                .selectinload(models.ClinicalTreatmentPlanItem.work_item)
                .selectinload(models.ClinicalWorkItem.targets)
            )
        )
        updated_phase = (await self.db.execute(stmt)).scalar_one()
        plan_reloaded = await self.get_plan(patient_id, plan_id)
        for ph in plan_reloaded.phases:
            if ph.id == updated_phase.id:
                return ph
        updated_phase.phase_estimated_total = 0.0
        updated_phase.unpriced_items_count = 0
        return updated_phase

    async def reorder_phases(
        self,
        patient_id: int,
        plan_id: int,
        data: schemas.ClinicalTreatmentPlanPhaseReorder,
    ) -> List[models.ClinicalTreatmentPlanPhase]:
        """
        Atomically reorder phases within a plan (G9-M03).
        Allowed only in 'draft' or 'proposed' status.
        Uses a temporary offset during flush to satisfy uq_ctpp_plan_phase_order and
        ck_ctpp_phase_order_non_negative simultaneously.
        Handles concurrent collisions on uq_ctpp_plan_phase_order with HTTP 409.
        """
        plan = await self._get_plan_and_verify(patient_id, plan_id)
        if plan.status not in ("draft", "proposed"):
            raise HTTPException(
                status_code=409,
                detail=f"Phases cannot be reordered in a plan in '{plan.status}' status",
            )

        stmt = (
            select(models.ClinicalTreatmentPlanPhase)
            .where(
                models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
                models.ClinicalTreatmentPlanPhase.plan_id == plan.id,
            )
            .order_by(models.ClinicalTreatmentPlanPhase.phase_order.asc())
        )
        existing_phases = list((await self.db.execute(stmt)).scalars().all())
        existing_by_id = {p.id: p for p in existing_phases}

        if len(data.phase_ids) != len(set(data.phase_ids)):
            raise HTTPException(status_code=422, detail="Duplicate phase IDs in reorder list")

        if set(data.phase_ids) != set(existing_by_id.keys()):
            raise HTTPException(
                status_code=422,
                detail="All phases of the plan must be included in reorder list",
            )

        # Temporary non-colliding offset >= 10000 to respect ck_ctpp_phase_order_non_negative
        # and prevent unique collisions on uq_ctpp_plan_phase_order
        TEMP_OFFSET = 10000
        try:
            for idx, pid in enumerate(data.phase_ids):
                existing_by_id[pid].phase_order = TEMP_OFFSET + idx
            await self.db.flush()

            for idx, pid in enumerate(data.phase_ids):
                existing_by_id[pid].phase_order = idx
            await self.db.commit()
        except (IntegrityError, StaleDataError):
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Concurrent phase reorder conflict; please refresh and try again",
            )

        plan_reloaded = await self.get_plan(patient_id, plan_id)
        return plan_reloaded.phases

    async def delete_phase(
        self,
        patient_id: int,
        plan_id: int,
        phase_id: int,
    ) -> None:
        """
        Delete a phase from a treatment plan (G9-M03).
        Allowed only in 'draft' or 'proposed' status (409 otherwise).
        Phase items cascade delete; underlying ClinicalWorkItems remain untouched.
        Remaining phases are re-compacted sequentially.
        """
        plan, phase = await self._get_phase_and_verify(patient_id, plan_id, phase_id)
        if plan.status not in ("draft", "proposed"):
            raise HTTPException(
                status_code=409,
                detail=f"Phases cannot be deleted from a plan in '{plan.status}' status",
            )

        try:
            await self.db.delete(phase)
            await self.db.flush()

            stmt_rem = (
                select(models.ClinicalTreatmentPlanPhase)
                .where(
                    models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
                    models.ClinicalTreatmentPlanPhase.plan_id == plan.id,
                )
                .order_by(models.ClinicalTreatmentPlanPhase.phase_order.asc())
            )
            remaining = list((await self.db.execute(stmt_rem)).scalars().all())
            if remaining:
                TEMP_OFFSET = 10000
                for idx, p in enumerate(remaining):
                    p.phase_order = TEMP_OFFSET + idx
                await self.db.flush()
                for idx, p in enumerate(remaining):
                    p.phase_order = idx

            await self.db.commit()
        except (IntegrityError, StaleDataError):
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Concurrent phase conflict during deletion; please refresh and try again",
            )

    async def add_work_item_to_phase(
        self,
        patient_id: int,
        plan_id: int,
        phase_id: int,
        data: schemas.ClinicalTreatmentPlanItemCreate,
    ) -> models.ClinicalTreatmentPlanItem:
        """
        Amendment B & C: Link existing ClinicalWorkItem into a treatment plan phase.
        Allowed only in 'draft' or 'proposed' status (Decision 4).
        Validates work item belongs to same tenant & patient, status != 'cancelled', kind == 'procedure' (Fix A).
        Duplicate work item in same phase -> 409.
        Multi-plan sharing allowed (same work item in multiple plans).
        """
        plan, phase = await self._get_phase_and_verify(patient_id, plan_id, phase_id)
        if plan.status not in ("draft", "proposed"):
            raise HTTPException(
                status_code=409,
                detail=f"Procedures cannot be added to a plan in '{plan.status}' status",
            )

        phase_id_val = phase.id

        stmt_wi = (
            select(models.ClinicalWorkItem)
            .where(
                models.ClinicalWorkItem.id == data.work_item_id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
            )
        )
        work_item = (await self.db.execute(stmt_wi)).scalar_one_or_none()
        if not work_item:
            raise HTTPException(status_code=404, detail="Work item not found for patient")
        if work_item.status == "cancelled":
            raise HTTPException(
                status_code=422,
                detail="Cancelled work item cannot be added to a treatment plan phase",
            )
        if getattr(work_item, "kind", None) != "procedure":
            raise HTTPException(
                status_code=422,
                detail="Only procedure work items can be added to a treatment plan phase; findings are not allowed",
            )

        work_item_id_val = work_item.id

        stmt_dup = select(models.ClinicalTreatmentPlanItem).where(
            models.ClinicalTreatmentPlanItem.tenant_id == self.tenant_id,
            models.ClinicalTreatmentPlanItem.phase_id == phase_id_val,
            models.ClinicalTreatmentPlanItem.work_item_id == work_item_id_val,
        )
        if (await self.db.execute(stmt_dup)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Work item is already attached to this phase")

        clean_notes = data.notes.strip() if data.notes else None

        async def _attempt_insert() -> models.ClinicalTreatmentPlanItem:
            max_order_stmt = select(func.max(models.ClinicalTreatmentPlanItem.item_order)).where(
                models.ClinicalTreatmentPlanItem.tenant_id == self.tenant_id,
                models.ClinicalTreatmentPlanItem.phase_id == phase_id_val,
            )
            max_order = (await self.db.execute(max_order_stmt)).scalar()
            next_order = (max_order + 1) if max_order is not None else 0

            item = models.ClinicalTreatmentPlanItem(
                tenant_id=self.tenant_id,
                phase_id=phase_id_val,
                work_item_id=work_item_id_val,
                item_order=next_order,
                status="planned",
                notes=clean_notes,
            )
            self.db.add(item)
            await self.db.flush()
            saved_item_id = item.id
            await self.db.commit()

            stmt_reload = (
                select(models.ClinicalTreatmentPlanItem)
                .where(
                    models.ClinicalTreatmentPlanItem.id == saved_item_id,
                    models.ClinicalTreatmentPlanItem.tenant_id == self.tenant_id,
                )
                .options(
                    selectinload(models.ClinicalTreatmentPlanItem.work_item)
                    .selectinload(models.ClinicalWorkItem.targets)
                )
                .execution_options(populate_existing=True)
            )
            inserted_item = (await self.db.execute(stmt_reload)).scalar_one_or_none() or item
            plan_reloaded = await self.get_plan(patient_id, plan_id)
            for ph in plan_reloaded.phases:
                if ph.id == phase_id:
                    for it in ph.items:
                        if it.id == inserted_item.id:
                            return it
            inserted_item.estimated_fee = 0.0
            inserted_item.unpriced = True
            return inserted_item

        try:
            return await _attempt_insert()
        except IntegrityError:
            await self.db.rollback()
            # Double check if duplicate work item was committed concurrently
            if (await self.db.execute(stmt_dup)).scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Work item is already attached to this phase")
            # Retry once for order collision
            try:
                return await _attempt_insert()
            except IntegrityError:
                await self.db.rollback()
                raise HTTPException(status_code=409, detail="Concurrent item conflict in phase")

    async def remove_work_item_from_phase(
        self,
        patient_id: int,
        plan_id: int,
        phase_id: int,
        item_id: int,
    ) -> None:
        """
        Unlink item from phase. Removes ClinicalTreatmentPlanItem row.
        Allowed only in 'draft' or 'proposed' status (Decision 4).
        Underlying ClinicalWorkItem is untouched.
        """
        plan, phase = await self._get_phase_and_verify(patient_id, plan_id, phase_id)
        if plan.status not in ("draft", "proposed"):
            raise HTTPException(
                status_code=409,
                detail=f"Procedures cannot be removed from a plan in '{plan.status}' status",
            )

        stmt_item = select(models.ClinicalTreatmentPlanItem).where(
            models.ClinicalTreatmentPlanItem.id == item_id,
            models.ClinicalTreatmentPlanItem.tenant_id == self.tenant_id,
            models.ClinicalTreatmentPlanItem.phase_id == phase.id,
        )
        item = (await self.db.execute(stmt_item)).scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Treatment plan item not found")

        await self.db.delete(item)
        await self.db.commit()

    async def transition_plan(
        self,
        patient_id: int,
        plan_id: int,
        to_status: str,
    ) -> models.ClinicalTreatmentPlan:
        """
        Transition clinical treatment plan status according to ALLOWED_PLAN_TRANSITIONS.
        Plan-level ONLY (does NOT alter work items, events, invoices, or treatments).
        Logs audit trail via log_admin_action (Decision 7).
        Maps StaleDataError to HTTP 409 (Decision 6).
        """
        plan = await self._get_plan_and_verify(patient_id, plan_id)

        current_status = plan.status
        allowed = ALLOWED_PLAN_TRANSITIONS.get(current_status, set())
        if to_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"Invalid transition from '{current_status}' to '{to_status}'",
            )

        old_status = plan.status
        plan.status = to_status

        active_user = await self._get_active_current_user()
        log_admin_action(
            db=self.db,
            admin_user=active_user,
            action=f"transition_{to_status}",
            entity_type="clinical_treatment_plan",
            entity_id=plan.id,
            old_value={"status": old_status},
            new_value={"status": to_status},
            details=f"Treatment plan #{plan.id} status transitioned from '{old_status}' to '{to_status}'",
            tenant_id=self.tenant_id,
        )

        try:
            await self.db.commit()
        except StaleDataError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Treatment plan was modified concurrently by another user",
            )

        stmt = (
            select(models.ClinicalTreatmentPlan)
            .where(
                models.ClinicalTreatmentPlan.id == plan.id,
                models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
            )
            .options(_eager_plan_options())
            .execution_options(populate_existing=True)
        )
        transitioned_plan = (await self.db.execute(stmt)).scalar_one()
        await self._attach_dynamic_estimates(patient_id, transitioned_plan)
        return transitioned_plan
