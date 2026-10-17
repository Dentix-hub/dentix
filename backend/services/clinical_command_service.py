"""
Clinical Command Service (Slice S04).
Domain service for native ClinicalWorkItem and ClinicalEvent mutations and queries.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.clinical.catalog import (
    CANONICAL_FINDING_CODES,
    CANONICAL_PROCEDURE_CODES,
    validate_treatment_status,
)
from backend.core.permissions import Permission, has_permission
from backend.schemas.clinical_commands import validate_target_shape
from backend.services.clinical_workspace_service import (
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    FEATURE_FLAG_CLINICAL_PRIMARY,
    FEATURE_FLAG_CLINICAL_SHADOW,
)
from backend.services.feature_service import FeatureFlagService
from backend.services.patient_access_service import ensure_patient_visible


class ClinicalCommandService:
    """
    Single domain service for native ClinicalWorkItem and ClinicalEvent mutations.
    Enforces native writes feature gating, doctor patient visibility, canonical catalog rules,
    terminal status immutability, optimistic concurrency locking, and event audit logging.
    """

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
        """Reload user if expired or detached from AsyncSession per R04."""
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

    async def is_native_writes_enabled(self) -> bool:
        """Check if native writes are enabled for current tenant."""
        return await FeatureFlagService.is_feature_enabled(
            self.db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, self.tenant_id
        )

    async def ensure_native_writes_enabled(self) -> None:
        """Fail-closed native writes gate (PD02 / R01)."""
        if not await self.is_native_writes_enabled():
            raise HTTPException(
                status_code=404,
                detail="Clinical native writes are disabled",
            )

    async def is_read_access_enabled(self) -> bool:
        """Check if read access is enabled via shadow, primary, or native writes flag."""
        flags = [
            FEATURE_FLAG_CLINICAL_SHADOW,
            FEATURE_FLAG_CLINICAL_PRIMARY,
            FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
        ]
        for flag in flags:
            if await FeatureFlagService.is_feature_enabled(self.db, flag, self.tenant_id):
                return True
        return False

    async def ensure_read_access_enabled(self) -> None:
        """Fail-closed read access gate."""
        if not await self.is_read_access_enabled():
            raise HTTPException(
                status_code=404,
                detail="Clinical workspace is disabled",
            )

    async def _ensure_patient_access(self, patient_id: int) -> None:
        """Verify patient visibility per R02."""
        user = await self._get_active_current_user()
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        await ensure_patient_visible(self.db, user, patient_id)

    async def _create_work_item_internal(
        self,
        patient_id: int,
        payload: schemas.ClinicalWorkItemCreate,
        now: datetime,
        payload_extra: Optional[dict] = None,
    ) -> models.ClinicalWorkItem:
        """Internal helper to build, validate and stage ClinicalWorkItem + ClinicalEvent without commit."""
        user = await self._get_active_current_user()
        user_role = getattr(user, "role", "guest")

        # RBAC enforcement per PD02a
        if payload.kind == "procedure":
            if not has_permission(user_role, Permission.TREATMENT_PLAN_WRITE):
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied. Required: treatment_plan:write for procedures",
                )
        elif payload.kind == "finding":
            if not has_permission(user_role, Permission.CLINICAL_WRITE):
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied. Required: clinical:write for findings",
                )
        else:
            raise HTTPException(status_code=422, detail=f"Invalid kind: '{payload.kind}'")

        # Canonical code validation
        if payload.kind == "finding" and payload.code not in CANONICAL_FINDING_CODES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid finding code '{payload.code}'. Allowed: {CANONICAL_FINDING_CODES}",
            )
        if payload.kind == "procedure" and payload.code not in CANONICAL_PROCEDURE_CODES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid procedure code '{payload.code}'. Allowed: {CANONICAL_PROCEDURE_CODES}",
            )

        try:
            validate_treatment_status(payload.status)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        if payload.status in ("superseded", "entered_in_error"):
            raise HTTPException(
                status_code=422,
                detail=f"Status '{payload.status}' cannot be set directly on creation",
            )

        # Shape validation on targets
        for t in payload.targets:
            try:
                validate_target_shape(
                    target_kind=t.target_kind,
                    tooth_key=t.tooth_key,
                    surface_code=t.surface_code,
                    root_id=t.root_id,
                    canal_id=t.canal_id,
                )
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

        work_item = models.ClinicalWorkItem(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            kind=payload.kind,
            code=payload.code,
            status=payload.status,
            notes=payload.notes,
            created_by_user_id=self.current_user_id,
            version_id=1,
            created_at=now,
            updated_at=now,
        )
        for t in payload.targets:
            work_item.targets.append(
                models.ClinicalWorkItemTarget(
                    tenant_id=self.tenant_id,
                    target_kind=t.target_kind,
                    tooth_key=t.tooth_key,
                    surface_code=t.surface_code,
                    root_id=t.root_id,
                    canal_id=t.canal_id,
                    created_at=now,
                )
            )
        self.db.add(work_item)
        await self.db.flush()

        # Atomically append corresponding recorded clinical event
        event_payload = {
            "kind": work_item.kind,
            "code": work_item.code,
            "status": work_item.status,
        }
        if payload_extra:
            event_payload.update(payload_extra)

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            work_item_id=work_item.id,
            event_type=f"{work_item.kind}_recorded",
            occurred_at=now,
            actor_user_id=self.current_user_id,
            payload=event_payload,
            notes=work_item.notes,
            created_at=now,
        )
        for t in payload.targets:
            event.targets.append(
                models.ClinicalEventTarget(
                    tenant_id=self.tenant_id,
                    target_kind=t.target_kind,
                    tooth_key=t.tooth_key,
                    surface_code=t.surface_code,
                    root_id=t.root_id,
                    canal_id=t.canal_id,
                    created_at=now,
                )
            )
        self.db.add(event)
        await self.db.flush()
        return work_item

    async def create_work_item(
        self,
        patient_id: int,
        payload: schemas.ClinicalWorkItemCreate,
    ) -> models.ClinicalWorkItem:
        """Create a clinical work item and atomically append a recorded event."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)
        now = datetime.now(timezone.utc)
        work_item = await self._create_work_item_internal(patient_id, payload, now=now)
        work_item_id = work_item.id
        await self.db.commit()

        stmt = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id == work_item_id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
        )
        reloaded = (await self.db.execute(stmt)).scalar_one()
        return reloaded

    async def create_finding(
        self,
        patient_id: int,
        payload: schemas.ClinicalFindingCreate,
    ) -> models.ClinicalWorkItem:
        """Create a single dedicated clinical finding."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)
        now = datetime.now(timezone.utc)
        wi_create = schemas.ClinicalWorkItemCreate(
            kind="finding",
            code=payload.code,
            status=payload.status,
            notes=payload.notes,
            targets=payload.targets,
        )
        payload_extra = {"severity": payload.severity} if payload.severity else None
        work_item = await self._create_work_item_internal(
            patient_id, wi_create, now=now, payload_extra=payload_extra
        )
        work_item_id = work_item.id
        await self.db.commit()

        stmt = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id == work_item_id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
        )
        reloaded = (await self.db.execute(stmt)).scalar_one()
        return reloaded

    async def create_findings_bulk(
        self,
        patient_id: int,
        payload: schemas.ClinicalFindingBulkCreate,
    ) -> schemas.ClinicalBulkWorkItemResponse:
        """Bulk create clinical findings in an atomic transaction (1 to 50 items)."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)

        user = await self._get_active_current_user()
        user_role = getattr(user, "role", "guest")
        if not has_permission(user_role, Permission.CLINICAL_WRITE):
            raise HTTPException(
                status_code=403,
                detail="Permission denied. Required: clinical:write for findings",
            )

        now = datetime.now(timezone.utc)
        created_ids: List[int] = []
        try:
            for item in payload.items:
                wi_create = schemas.ClinicalWorkItemCreate(
                    kind="finding",
                    code=item.code,
                    status=item.status,
                    notes=item.notes,
                    targets=item.targets,
                )
                payload_extra = {"severity": item.severity} if item.severity else None
                wi = await self._create_work_item_internal(
                    patient_id, wi_create, now=now, payload_extra=payload_extra
                )
                created_ids.append(wi.id)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        stmt = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id.in_(created_ids),
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
            .order_by(models.ClinicalWorkItem.id.asc())
        )
        reloaded = (await self.db.execute(stmt)).scalars().all()
        return schemas.ClinicalBulkWorkItemResponse(
            items=[schemas.ClinicalWorkItemRead.model_validate(item) for item in reloaded],
            count=len(reloaded),
        )

    async def create_procedure(
        self,
        patient_id: int,
        payload: schemas.ClinicalProcedureCreate,
    ) -> models.ClinicalWorkItem:
        """Create a single dedicated clinical procedure."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)
        now = datetime.now(timezone.utc)
        wi_create = schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code=payload.code,
            status=payload.status,
            notes=payload.notes,
            targets=payload.targets,
        )
        work_item = await self._create_work_item_internal(patient_id, wi_create, now=now)
        work_item_id = work_item.id
        await self.db.commit()

        stmt = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id == work_item_id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
        )
        reloaded = (await self.db.execute(stmt)).scalar_one()
        return reloaded

    async def create_procedures_bulk(
        self,
        patient_id: int,
        payload: schemas.ClinicalProcedureBulkCreate,
    ) -> schemas.ClinicalBulkWorkItemResponse:
        """Bulk create clinical procedures in an atomic transaction (1 to 50 items)."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)

        user = await self._get_active_current_user()
        user_role = getattr(user, "role", "guest")
        if not has_permission(user_role, Permission.TREATMENT_PLAN_WRITE):
            raise HTTPException(
                status_code=403,
                detail="Permission denied. Required: treatment_plan:write for procedures",
            )

        now = datetime.now(timezone.utc)
        created_ids: List[int] = []
        try:
            for item in payload.items:
                wi_create = schemas.ClinicalWorkItemCreate(
                    kind="procedure",
                    code=item.code,
                    status=item.status,
                    notes=item.notes,
                    targets=item.targets,
                )
                wi = await self._create_work_item_internal(patient_id, wi_create, now=now)
                created_ids.append(wi.id)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        stmt = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id.in_(created_ids),
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
            .order_by(models.ClinicalWorkItem.id.asc())
        )
        reloaded = (await self.db.execute(stmt)).scalars().all()
        return schemas.ClinicalBulkWorkItemResponse(
            items=[schemas.ClinicalWorkItemRead.model_validate(item) for item in reloaded],
            count=len(reloaded),
        )

    async def update_work_item(
        self,
        patient_id: int,
        work_item_id: int,
        payload: schemas.ClinicalWorkItemUpdate,
    ) -> models.ClinicalWorkItem:
        """Update a clinical work item and atomically append an updated event."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)

        stmt = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id == work_item_id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
        )
        res = await self.db.execute(stmt)
        work_item = res.scalar_one_or_none()
        if not work_item or work_item.patient_id != patient_id:
            raise HTTPException(status_code=404, detail="Clinical work item not found")

        user = await self._get_active_current_user()
        user_role = getattr(user, "role", "guest")

        # RBAC per PD02a based on stored item kind
        if work_item.kind == "procedure":
            if not has_permission(user_role, Permission.TREATMENT_PLAN_WRITE):
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied. Required: treatment_plan:write for procedures",
                )
        elif work_item.kind == "finding":
            if not has_permission(user_role, Permission.CLINICAL_WRITE):
                raise HTTPException(
                    status_code=403,
                    detail="Permission denied. Required: clinical:write for findings",
                )

        # Stale version check (G7-M16 / R04)
        if payload.expected_version_id is not None and work_item.version_id != payload.expected_version_id:
            raise HTTPException(
                status_code=409,
                detail=f"Stale version: expected {payload.expected_version_id}, found {work_item.version_id}",
            )

        # Status transition checks
        if payload.status is not None:
            try:
                validate_treatment_status(payload.status)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

            if payload.status in ("superseded", "entered_in_error"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Status '{payload.status}' cannot be set via PATCH. Use correction endpoints.",
                )

            if work_item.status in ("completed", "cancelled") and payload.status != work_item.status:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot transition from terminal status '{work_item.status}' to '{payload.status}'",
                )
            work_item.status = payload.status

        if payload.notes is not None:
            work_item.notes = payload.notes

        now = datetime.now(timezone.utc)
        work_item.updated_at = now

        if payload.targets is not None:
            for t in payload.targets:
                try:
                    validate_target_shape(
                        target_kind=t.target_kind,
                        tooth_key=t.tooth_key,
                        surface_code=t.surface_code,
                        root_id=t.root_id,
                        canal_id=t.canal_id,
                    )
                except ValueError as e:
                    raise HTTPException(status_code=422, detail=str(e))

            work_item.targets.clear()
            for t in payload.targets:
                work_item.targets.append(
                    models.ClinicalWorkItemTarget(
                        tenant_id=self.tenant_id,
                        target_kind=t.target_kind,
                        tooth_key=t.tooth_key,
                        surface_code=t.surface_code,
                        root_id=t.root_id,
                        canal_id=t.canal_id,
                        created_at=now,
                    )
                )

        # Atomically append updated event with matching targets
        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            work_item_id=work_item.id,
            event_type=f"{work_item.kind}_updated",
            occurred_at=now,
            actor_user_id=self.current_user_id,
            payload={
                "kind": work_item.kind,
                "code": work_item.code,
                "status": work_item.status,
                "version_id": work_item.version_id + 1,
            },
            notes=work_item.notes,
            created_at=now,
        )
        for t in work_item.targets:
            event.targets.append(
                models.ClinicalEventTarget(
                    tenant_id=self.tenant_id,
                    target_kind=t.target_kind,
                    tooth_key=t.tooth_key,
                    surface_code=t.surface_code,
                    root_id=t.root_id,
                    canal_id=t.canal_id,
                    created_at=now,
                )
            )
        self.db.add(event)

        try:
            await self.db.commit()
        except StaleDataError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Concurrent modification detected (stale version)",
            )

        stmt_reload = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id == work_item.id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
        )
        reloaded = (await self.db.execute(stmt_reload)).scalar_one()
        return reloaded

    async def list_work_items(
        self,
        patient_id: int,
        include_corrected: bool = False,
    ) -> List[models.ClinicalWorkItem]:
        """List patient clinical work items, excluding corrected items by default."""
        await self.ensure_read_access_enabled()
        await self._ensure_patient_access(patient_id)

        user = await self._get_active_current_user()
        user_role = getattr(user, "role", "guest")
        if not has_permission(user_role, Permission.CLINICAL_READ):
            raise HTTPException(
                status_code=403,
                detail="Permission denied. Required: clinical:read",
            )

        stmt = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
            )
        )
        if not include_corrected:
            stmt = stmt.where(
                models.ClinicalWorkItem.status.not_in(["superseded", "entered_in_error"])
            )
        stmt = stmt.order_by(models.ClinicalWorkItem.id.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
