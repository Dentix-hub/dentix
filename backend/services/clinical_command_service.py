"""
Clinical Command Service (Slice S04).
Domain service for native ClinicalWorkItem and ClinicalEvent mutations and queries.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError


from backend import models, schemas


def compute_request_fingerprint(data: dict) -> str:
    """Deterministic SHA256 digest of request parameters."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_target(t: schemas.ClinicalTargetInput) -> dict:
    return {
        "target_kind": t.target_kind,
        "tooth_key": str(t.tooth_key),
        "surface_code": t.surface_code,
        "root_id": t.root_id,
        "canal_id": t.canal_id,
    }
from backend.clinical.catalog import (
    CANONICAL_CORRECTION_STATUSES,
    CANONICAL_FINDING_CODES,
    CANONICAL_PROCEDURE_CODES,
    CORRECTION_STATUS_ENTERED_IN_ERROR,
    CORRECTION_STATUS_SUPERSEDED,
    validate_treatment_status,
)
from backend.core.permissions import Permission, has_permission
from backend.models.clinical_core import FDI_TOOTH_KEYS
from backend.schemas.clinical_commands import validate_target_shape
from backend.services.clinical_workspace_service import (
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    FEATURE_FLAG_CLINICAL_PRIMARY,
    FEATURE_FLAG_CLINICAL_SHADOW,
    ClinicalWorkspaceService as ClinicalWorkspaceSnapshotService,
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

    def _validate_idempotency_key(self, key: Optional[str]) -> Optional[str]:
        if key is None:
            return None
        if len(key) > 128:
            raise HTTPException(
                status_code=422,
                detail="Idempotency key exceeds maximum length of 128 characters",
            )
        if len(key.strip()) == 0:
            raise HTTPException(
                status_code=422,
                detail="Idempotency key cannot be empty",
            )
        return key.strip()

    async def _acquire_advisory_lock(self, key: str) -> None:
        """
        Acquire PostgreSQL transaction-level advisory lock (R05).
        Serializes concurrent requests with the same (tenant_id, key).
        No-op on SQLite.
        """
        bind = getattr(self.db, "bind", None)
        if bind is None and hasattr(self.db, "get_bind"):
            try:
                bind = self.db.get_bind()
            except Exception:
                bind = None
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name == "postgresql":
            lock_key = f"{self.tenant_id}:{key}"
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )

    async def _find_idempotent_event(
        self, patient_id: int, idempotency_key: str, fingerprint: str
    ) -> Optional[models.ClinicalEvent]:
        """
        Locate existing event with matching idempotency key for this patient and tenant.
        Raises 409 Conflict if key matches but fingerprint differs.
        Returns matching ClinicalEvent if found, None otherwise.
        Uses portable Python-level inspection matching TreatmentService._find_linked_clinical_work_item.
        """
        stmt = (
            select(models.ClinicalEvent)
            .where(
                models.ClinicalEvent.tenant_id == self.tenant_id,
                models.ClinicalEvent.patient_id == patient_id,
            )
            .order_by(models.ClinicalEvent.id.desc())
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()
        for ev in events:
            if isinstance(ev.payload, dict) and ev.payload.get("idempotency_key") == idempotency_key:
                stored_fp = ev.payload.get("request_fingerprint")
                if stored_fp != fingerprint:
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency key already used with different parameters",
                    )
                return ev
        return None

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
        idempotency_key: Optional[str] = None,
    ) -> models.ClinicalWorkItem:
        """Create a clinical work item and atomically append a recorded event."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)

        key = self._validate_idempotency_key(idempotency_key or getattr(payload, "idempotency_key", None))
        fingerprint = None
        if key:
            await self._acquire_advisory_lock(key)
            fp_data = {
                "action": "create_work_item",
                "kind": payload.kind,
                "code": payload.code,
                "status": payload.status,
                "notes": payload.notes or "",
                "targets": sorted(
                    [_normalize_target(t) for t in payload.targets],
                    key=lambda x: (x["target_kind"], x["tooth_key"], x["surface_code"] or "", x["root_id"] or "", x["canal_id"] or ""),
                ),
            }
            fingerprint = compute_request_fingerprint(fp_data)
            existing_ev = await self._find_idempotent_event(patient_id, key, fingerprint)
            if existing_ev:
                stmt = (
                    select(models.ClinicalWorkItem)
                    .options(selectinload(models.ClinicalWorkItem.targets))
                    .where(
                        models.ClinicalWorkItem.id == existing_ev.work_item_id,
                        models.ClinicalWorkItem.tenant_id == self.tenant_id,
                    )
                )
                return (await self.db.execute(stmt)).scalar_one()

        now = datetime.now(timezone.utc)
        payload_extra = None
        if key and fingerprint:
            payload_extra = {"idempotency_key": key, "request_fingerprint": fingerprint}

        work_item = await self._create_work_item_internal(
            patient_id, payload, now=now, payload_extra=payload_extra
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

    async def create_finding(
        self,
        patient_id: int,
        payload: schemas.ClinicalFindingCreate,
        idempotency_key: Optional[str] = None,
    ) -> models.ClinicalWorkItem:
        """Create a single dedicated clinical finding."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)

        key = self._validate_idempotency_key(idempotency_key or getattr(payload, "idempotency_key", None))
        fingerprint = None
        if key:
            await self._acquire_advisory_lock(key)
            fp_data = {
                "action": "create_finding",
                "code": payload.code,
                "status": payload.status,
                "notes": payload.notes or "",
                "severity": payload.severity,
                "targets": sorted(
                    [_normalize_target(t) for t in payload.targets],
                    key=lambda x: (x["target_kind"], x["tooth_key"], x["surface_code"] or "", x["root_id"] or "", x["canal_id"] or ""),
                ),
            }
            fingerprint = compute_request_fingerprint(fp_data)
            existing_ev = await self._find_idempotent_event(patient_id, key, fingerprint)
            if existing_ev:
                stmt = (
                    select(models.ClinicalWorkItem)
                    .options(selectinload(models.ClinicalWorkItem.targets))
                    .where(
                        models.ClinicalWorkItem.id == existing_ev.work_item_id,
                        models.ClinicalWorkItem.tenant_id == self.tenant_id,
                    )
                )
                return (await self.db.execute(stmt)).scalar_one()

        now = datetime.now(timezone.utc)
        wi_create = schemas.ClinicalWorkItemCreate(
            kind="finding",
            code=payload.code,
            status=payload.status,
            notes=payload.notes,
            targets=payload.targets,
        )
        payload_extra = {}
        if payload.severity:
            payload_extra["severity"] = payload.severity
        if key and fingerprint:
            payload_extra["idempotency_key"] = key
            payload_extra["request_fingerprint"] = fingerprint

        work_item = await self._create_work_item_internal(
            patient_id, wi_create, now=now, payload_extra=payload_extra or None
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
        idempotency_key: Optional[str] = None,
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

        key = self._validate_idempotency_key(idempotency_key or getattr(payload, "idempotency_key", None))
        fingerprint = None
        if key:
            await self._acquire_advisory_lock(key)
            fp_data = {
                "action": "create_findings_bulk",
                "items": [
                    {
                        "code": item.code,
                        "status": item.status,
                        "notes": item.notes or "",
                        "severity": item.severity,
                        "targets": sorted(
                            [_normalize_target(t) for t in item.targets],
                            key=lambda x: (x["target_kind"], x["tooth_key"], x["surface_code"] or "", x["root_id"] or "", x["canal_id"] or ""),
                        ),
                    }
                    for item in payload.items
                ],
            }
            fingerprint = compute_request_fingerprint(fp_data)
            existing_ev = await self._find_idempotent_event(patient_id, key, fingerprint)
            if existing_ev:
                bulk_ids = existing_ev.payload.get("bulk_work_item_ids", [existing_ev.work_item_id])
                stmt = (
                    select(models.ClinicalWorkItem)
                    .options(selectinload(models.ClinicalWorkItem.targets))
                    .where(
                        models.ClinicalWorkItem.id.in_(bulk_ids),
                        models.ClinicalWorkItem.tenant_id == self.tenant_id,
                    )
                    .order_by(models.ClinicalWorkItem.id.asc())
                )
                reloaded = (await self.db.execute(stmt)).scalars().all()
                return schemas.ClinicalBulkWorkItemResponse(
                    items=[schemas.ClinicalWorkItemRead.model_validate(item) for item in reloaded],
                    count=len(reloaded),
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

            if key and fingerprint:
                stmt_evs = select(models.ClinicalEvent).where(
                    models.ClinicalEvent.work_item_id.in_(created_ids),
                    models.ClinicalEvent.tenant_id == self.tenant_id,
                )
                evs = (await self.db.execute(stmt_evs)).scalars().all()
                for ev in evs:
                    p = dict(ev.payload or {})
                    p["idempotency_key"] = key
                    p["request_fingerprint"] = fingerprint
                    p["bulk_work_item_ids"] = created_ids
                    ev.payload = p

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
        idempotency_key: Optional[str] = None,
    ) -> models.ClinicalWorkItem:
        """Create a single dedicated clinical procedure."""
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)

        key = self._validate_idempotency_key(idempotency_key or getattr(payload, "idempotency_key", None))
        fingerprint = None
        if key:
            await self._acquire_advisory_lock(key)
            fp_data = {
                "action": "create_procedure",
                "code": payload.code,
                "status": payload.status,
                "notes": payload.notes or "",
                "targets": sorted(
                    [_normalize_target(t) for t in payload.targets],
                    key=lambda x: (x["target_kind"], x["tooth_key"], x["surface_code"] or "", x["root_id"] or "", x["canal_id"] or ""),
                ),
            }
            fingerprint = compute_request_fingerprint(fp_data)
            existing_ev = await self._find_idempotent_event(patient_id, key, fingerprint)
            if existing_ev:
                stmt = (
                    select(models.ClinicalWorkItem)
                    .options(selectinload(models.ClinicalWorkItem.targets))
                    .where(
                        models.ClinicalWorkItem.id == existing_ev.work_item_id,
                        models.ClinicalWorkItem.tenant_id == self.tenant_id,
                    )
                )
                return (await self.db.execute(stmt)).scalar_one()

        now = datetime.now(timezone.utc)
        wi_create = schemas.ClinicalWorkItemCreate(
            kind="procedure",
            code=payload.code,
            status=payload.status,
            notes=payload.notes,
            targets=payload.targets,
        )
        payload_extra = None
        if key and fingerprint:
            payload_extra = {"idempotency_key": key, "request_fingerprint": fingerprint}

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

    async def create_procedures_bulk(
        self,
        patient_id: int,
        payload: schemas.ClinicalProcedureBulkCreate,
        idempotency_key: Optional[str] = None,
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

        key = self._validate_idempotency_key(idempotency_key or getattr(payload, "idempotency_key", None))
        fingerprint = None
        if key:
            await self._acquire_advisory_lock(key)
            fp_data = {
                "action": "create_procedures_bulk",
                "items": [
                    {
                        "code": item.code,
                        "status": item.status,
                        "notes": item.notes or "",
                        "targets": sorted(
                            [_normalize_target(t) for t in item.targets],
                            key=lambda x: (x["target_kind"], x["tooth_key"], x["surface_code"] or "", x["root_id"] or "", x["canal_id"] or ""),
                        ),
                    }
                    for item in payload.items
                ],
            }
            fingerprint = compute_request_fingerprint(fp_data)
            existing_ev = await self._find_idempotent_event(patient_id, key, fingerprint)
            if existing_ev:
                bulk_ids = existing_ev.payload.get("bulk_work_item_ids", [existing_ev.work_item_id])
                stmt = (
                    select(models.ClinicalWorkItem)
                    .options(selectinload(models.ClinicalWorkItem.targets))
                    .where(
                        models.ClinicalWorkItem.id.in_(bulk_ids),
                        models.ClinicalWorkItem.tenant_id == self.tenant_id,
                    )
                    .order_by(models.ClinicalWorkItem.id.asc())
                )
                reloaded = (await self.db.execute(stmt)).scalars().all()
                return schemas.ClinicalBulkWorkItemResponse(
                    items=[schemas.ClinicalWorkItemRead.model_validate(item) for item in reloaded],
                    count=len(reloaded),
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

            if key and fingerprint:
                stmt_evs = select(models.ClinicalEvent).where(
                    models.ClinicalEvent.work_item_id.in_(created_ids),
                    models.ClinicalEvent.tenant_id == self.tenant_id,
                )
                evs = (await self.db.execute(stmt_evs)).scalars().all()
                for ev in evs:
                    p = dict(ev.payload or {})
                    p["idempotency_key"] = key
                    p["request_fingerprint"] = fingerprint
                    p["bulk_work_item_ids"] = created_ids
                    ev.payload = p

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

    async def correct_work_item(
        self,
        patient_id: int,
        work_item_id: int,
        payload: schemas.ClinicalWorkItemCorrectionCreate,
        idempotency_key: Optional[str] = None,
    ) -> schemas.ClinicalWorkItemCorrectionResponse:
        """
        Correct a clinical work item via entered_in_error or supersede mode (Slice S06 / G7-M08).
        Enforces native writes feature gating, doctor patient visibility, RBAC (TREATMENT_PLAN_WRITE only per PD02b),
        status guards (409 if already corrected), optimistic concurrency (409 on version mismatch or StaleDataError),
        and atomicity (zero clinical event mutation or deletion).
        """
        await self.ensure_native_writes_enabled()
        await self._ensure_patient_access(patient_id)

        user = await self._get_active_current_user()
        user_role = getattr(user, "role", "guest")
        if not has_permission(user_role, Permission.TREATMENT_PLAN_WRITE):
            raise HTTPException(
                status_code=403,
                detail="Permission denied. Required: treatment_plan:write for work item correction",
            )

        if not work_item_id or work_item_id <= 0:
            raise HTTPException(
                status_code=422,
                detail="Standalone events without a clinical work item cannot be corrected via work-item correction",
            )

        key = self._validate_idempotency_key(idempotency_key or getattr(payload, "idempotency_key", None))
        fingerprint = None
        if key:
            await self._acquire_advisory_lock(key)
            fp_data = {
                "action": "correct_work_item",
                "work_item_id": work_item_id,
                "mode": payload.mode,
                "reason": payload.reason,
                "expected_version_id": payload.expected_version_id,
                "replacement": {
                    "kind": payload.replacement.kind,
                    "code": payload.replacement.code,
                    "status": payload.replacement.status,
                    "notes": payload.replacement.notes or "",
                    "targets": sorted(
                        [_normalize_target(t) for t in payload.replacement.targets],
                        key=lambda x: (x["target_kind"], x["tooth_key"], x["surface_code"] or "", x["root_id"] or "", x["canal_id"] or ""),
                    ),
                } if payload.replacement else None,
            }
            fingerprint = compute_request_fingerprint(fp_data)
            existing_ev = await self._find_idempotent_event(patient_id, key, fingerprint)
            if existing_ev:
                stmt_orig = (
                    select(models.ClinicalWorkItem)
                    .options(selectinload(models.ClinicalWorkItem.targets))
                    .where(
                        models.ClinicalWorkItem.id == work_item_id,
                        models.ClinicalWorkItem.tenant_id == self.tenant_id,
                    )
                )
                reloaded_orig = (await self.db.execute(stmt_orig)).scalar_one()
                reloaded_repl = None
                repl_id = existing_ev.payload.get("replacement_work_item_id")
                if repl_id:
                    stmt_repl = (
                        select(models.ClinicalWorkItem)
                        .options(selectinload(models.ClinicalWorkItem.targets))
                        .where(
                            models.ClinicalWorkItem.id == repl_id,
                            models.ClinicalWorkItem.tenant_id == self.tenant_id,
                        )
                    )
                    reloaded_repl = (await self.db.execute(stmt_repl)).scalar_one_or_none()

                return schemas.ClinicalWorkItemCorrectionResponse(
                    original_work_item=schemas.ClinicalWorkItemRead.model_validate(reloaded_orig),
                    replacement_work_item=schemas.ClinicalWorkItemRead.model_validate(reloaded_repl) if reloaded_repl else None,
                    correction_event_id=existing_ev.id,
                    mode=existing_ev.payload.get("mode", payload.mode),
                    reason=existing_ev.payload.get("reason", payload.reason),
                )

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
            # Check if caller passed an event ID for an unlinked standalone event
            ev_stmt = select(models.ClinicalEvent).where(
                models.ClinicalEvent.id == work_item_id,
                models.ClinicalEvent.tenant_id == self.tenant_id,
                models.ClinicalEvent.patient_id == patient_id,
            )
            ev = (await self.db.execute(ev_stmt)).scalar_one_or_none()
            if ev and ev.work_item_id is None:
                raise HTTPException(
                    status_code=422,
                    detail="Standalone events without a clinical work item cannot be corrected via work-item correction",
                )
            raise HTTPException(status_code=404, detail="Clinical work item not found")

        # Double correction guard: 409 if already entered_in_error or superseded
        if work_item.status in (
            CORRECTION_STATUS_ENTERED_IN_ERROR,
            CORRECTION_STATUS_SUPERSEDED,
            "entered-in-error",
        ):
            raise HTTPException(
                status_code=409,
                detail=f"Work item is already corrected (status: '{work_item.status}')",
            )

        # Stale version check (G7-M16 / R04)
        if payload.expected_version_id is not None and work_item.version_id != payload.expected_version_id:
            raise HTTPException(
                status_code=409,
                detail=f"Stale version: expected {payload.expected_version_id}, found {work_item.version_id}",
            )

        now = datetime.now(timezone.utc)
        replacement_work_item: Optional[models.ClinicalWorkItem] = None

        if payload.mode == "entered_in_error":
            work_item.status = CORRECTION_STATUS_ENTERED_IN_ERROR
            work_item.updated_at = now
            ev_payload = {
                "mode": "entered_in_error",
                "work_item_id": work_item.id,
                "reason": payload.reason,
            }
            if key and fingerprint:
                ev_payload["idempotency_key"] = key
                ev_payload["request_fingerprint"] = fingerprint

            correction_event = models.ClinicalEvent(
                tenant_id=self.tenant_id,
                patient_id=patient_id,
                work_item_id=work_item.id,
                event_type="entered_in_error",
                occurred_at=now,
                actor_user_id=self.current_user_id,
                payload=ev_payload,
                notes=payload.reason,
                created_at=now,
            )
            for t in work_item.targets:
                correction_event.targets.append(
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
            self.db.add(correction_event)

        elif payload.mode == "supersede":
            if not payload.replacement:
                raise HTTPException(
                    status_code=422,
                    detail="Replacement work item is required when mode is 'supersede'",
                )
            if payload.replacement.status not in ("proposed", "planned"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Replacement work item status must be 'proposed' or 'planned', got '{payload.replacement.status}'",
                )

            work_item.status = CORRECTION_STATUS_SUPERSEDED
            work_item.updated_at = now

            replacement_work_item = await self._create_work_item_internal(
                patient_id, payload.replacement, now=now
            )

            ev_payload = {
                "mode": "supersede",
                "original_work_item_id": work_item.id,
                "replacement_work_item_id": replacement_work_item.id,
                "reason": payload.reason,
            }
            if key and fingerprint:
                ev_payload["idempotency_key"] = key
                ev_payload["request_fingerprint"] = fingerprint

            correction_event = models.ClinicalEvent(
                tenant_id=self.tenant_id,
                patient_id=patient_id,
                work_item_id=work_item.id,
                event_type="superseded",
                occurred_at=now,
                actor_user_id=self.current_user_id,
                payload=ev_payload,
                notes=payload.reason,
                created_at=now,
            )
            for t in work_item.targets:
                correction_event.targets.append(
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
            self.db.add(correction_event)
        else:
            raise HTTPException(status_code=422, detail=f"Invalid correction mode: '{payload.mode}'")

        try:
            await self.db.commit()
        except StaleDataError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Concurrent modification detected (stale version)",
            )

        # Reload original and replacement work items
        stmt_reload_orig = (
            select(models.ClinicalWorkItem)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.id == work_item.id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
            )
        )
        reloaded_orig = (await self.db.execute(stmt_reload_orig)).scalar_one()

        reloaded_repl: Optional[models.ClinicalWorkItem] = None
        if replacement_work_item:
            stmt_reload_repl = (
                select(models.ClinicalWorkItem)
                .options(selectinload(models.ClinicalWorkItem.targets))
                .where(
                    models.ClinicalWorkItem.id == replacement_work_item.id,
                    models.ClinicalWorkItem.tenant_id == self.tenant_id,
                )
            )
            reloaded_repl = (await self.db.execute(stmt_reload_repl)).scalar_one()

        return schemas.ClinicalWorkItemCorrectionResponse(
            original_work_item=schemas.ClinicalWorkItemRead.model_validate(reloaded_orig),
            replacement_work_item=schemas.ClinicalWorkItemRead.model_validate(reloaded_repl) if reloaded_repl else None,
            correction_event_id=correction_event.id,
            mode=payload.mode,
            reason=payload.reason,
        )

    async def get_tooth_detail(
        self,
        patient_id: int,
        tooth_key: str,
    ) -> schemas.ClinicalToothDetailRead:
        """
        Get tooth detail (Slice S06 / G7-M10).
        Validates tooth_key in FDI_TOOTH_KEYS (422 otherwise).
        Returns workspace projection tooth summary, work items targeting tooth,
        clinical events targeting tooth, and legacy treatments/tooth-statuses.
        """
        await self.ensure_read_access_enabled()
        await self._ensure_patient_access(patient_id)

        user = await self._get_active_current_user()
        user_role = getattr(user, "role", "guest")
        if not has_permission(user_role, Permission.CLINICAL_READ):
            raise HTTPException(
                status_code=403,
                detail="Permission denied. Required: clinical:read",
            )

        if tooth_key not in FDI_TOOTH_KEYS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid tooth_key '{tooth_key}'. Must be a valid FDI 2-digit tooth key.",
            )

        # 1. Summary from workspace snapshot
        ws_service = ClinicalWorkspaceSnapshotService(self.db, self.tenant_id, user)
        snapshot = await ws_service.get_workspace_snapshot(patient_id)
        summary: Optional[schemas.WorkspaceToothSummary] = None
        if snapshot and snapshot.teeth and tooth_key in snapshot.teeth:
            summary = snapshot.teeth[tooth_key]

        # 2. Active & historical work items targeting tooth_key
        wi_stmt = (
            select(models.ClinicalWorkItem)
            .join(models.ClinicalWorkItem.targets)
            .options(selectinload(models.ClinicalWorkItem.targets))
            .where(
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
                models.ClinicalWorkItemTarget.tooth_key == tooth_key,
            )
            .distinct()
            .order_by(models.ClinicalWorkItem.id.asc())
        )
        wi_rows = (await self.db.execute(wi_stmt)).scalars().all()
        work_items = [schemas.ClinicalWorkItemRead.model_validate(wi) for wi in wi_rows]

        # 3. Clinical events targeting tooth_key
        ev_stmt = (
            select(models.ClinicalEvent)
            .join(models.ClinicalEvent.targets)
            .options(selectinload(models.ClinicalEvent.targets))
            .where(
                models.ClinicalEvent.tenant_id == self.tenant_id,
                models.ClinicalEvent.patient_id == patient_id,
                models.ClinicalEventTarget.tooth_key == tooth_key,
            )
            .distinct()
            .order_by(models.ClinicalEvent.occurred_at.desc(), models.ClinicalEvent.id.desc())
        )
        ev_rows = (await self.db.execute(ev_stmt)).scalars().all()
        events = [schemas.ClinicalEventRead.model_validate(ev) for ev in ev_rows]

        # 4. Legacy records for tooth_key
        tooth_num = int(tooth_key) if tooth_key.isdigit() else None
        legacy_treatments: List[schemas.Treatment] = []
        legacy_tooth_statuses: List[schemas.ToothStatus] = []

        if tooth_num is not None:
            t_stmt = (
                select(models.Treatment)
                .options(selectinload(models.Treatment.treatment_sessions))
                .where(
                    models.Treatment.tenant_id == self.tenant_id,
                    models.Treatment.patient_id == patient_id,
                    models.Treatment.tooth_number == tooth_num,
                )
                .order_by(models.Treatment.id.asc())
            )
            t_rows = (await self.db.execute(t_stmt)).scalars().all()
            legacy_treatments = [schemas.Treatment.model_validate(t) for t in t_rows]

            ts_stmt = (
                select(models.ToothStatus)
                .where(
                    models.ToothStatus.tenant_id == self.tenant_id,
                    models.ToothStatus.patient_id == patient_id,
                    models.ToothStatus.tooth_number == tooth_num,
                )
                .order_by(models.ToothStatus.id.asc())
            )
            ts_rows = (await self.db.execute(ts_stmt)).scalars().all()
            legacy_tooth_statuses = [schemas.ToothStatus.model_validate(ts) for ts in ts_rows]

        return schemas.ClinicalToothDetailRead(
            tooth_key=tooth_key,
            summary=summary,
            work_items=work_items,
            events=events,
            legacy_treatments=legacy_treatments,
            legacy_tooth_statuses=legacy_tooth_statuses,
        )

    async def list_patient_events(
        self,
        patient_id: int,
        include_entered_in_error: bool = False,
    ) -> List[schemas.ClinicalEventRead]:
        """
        List raw patient clinical events (Slice S06 / G7-M11).
        Reads raw ClinicalEvent rows directly from database.
        Default (include_entered_in_error=False) excludes events where event_type is
        in CANONICAL_CORRECTION_STATUSES or attached work_item.status is in CANONICAL_CORRECTION_STATUSES.
        When include_entered_in_error=True, returns all raw events ordered by occurred_at DESC, id DESC.
        """
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
            select(models.ClinicalEvent)
            .outerjoin(models.ClinicalWorkItem, models.ClinicalEvent.work_item_id == models.ClinicalWorkItem.id)
            .options(selectinload(models.ClinicalEvent.targets))
            .where(
                models.ClinicalEvent.tenant_id == self.tenant_id,
                models.ClinicalEvent.patient_id == patient_id,
            )
        )
        if not include_entered_in_error:
            corr_statuses = (
                CORRECTION_STATUS_ENTERED_IN_ERROR,
                CORRECTION_STATUS_SUPERSEDED,
                "entered-in-error",
            )
            stmt = stmt.where(
                models.ClinicalEvent.event_type.not_in(corr_statuses),
                (models.ClinicalEvent.work_item_id.is_(None))
                | (models.ClinicalWorkItem.status.not_in(corr_statuses)),
            )

        stmt = stmt.order_by(models.ClinicalEvent.occurred_at.desc(), models.ClinicalEvent.id.desc())
        ev_rows = (await self.db.execute(stmt)).scalars().all()
        return [schemas.ClinicalEventRead.model_validate(ev) for ev in ev_rows]
