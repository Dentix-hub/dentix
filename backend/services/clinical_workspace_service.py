"""
Clinical Workspace Service (Issue #205).

Implements:
- Patient-scoped current Clinical Workspace Snapshot read.
- Pure deterministic reduction of native truth (occurred_at -> recorded_at -> stable ID).
- Exclusion of superseded and entered-in-error meaning without deleting history.
- Explicit fallback precedence for UNCOVERED and PARTIAL domains.
- Neutral preservation of unsupported clinical codes as unclassified warnings.
- Zero finance exposure and zero mutation authority.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Literal, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud, models, schemas
from backend.services.feature_service import FeatureFlagService
from backend.clinical.catalog import (
    CANONICAL_FINDING_CODES,
    CANONICAL_TOOTH_LIFECYCLE_CODES,
    FROZEN_RENDERER_PROCEDURE_CODES,
    FindingCode,
    ProcedureCode,
    ToothLifecycleCode,
)
from backend.clinical.legacy_mapping import (
    VerifiedPatientContext,
    map_legacy_clinical_batch,
)
from backend.models.clinical_core import FDI_TOOTH_KEYS

logger = logging.getLogger("smart_clinic")

FEATURE_FLAG_CLINICAL_SHADOW = "clinical_vnext_shadow"
FEATURE_FLAG_CLINICAL_PRIMARY = "clinical_vnext_primary"
FEATURE_FLAG_CLINICAL_NATIVE_WRITES = "clinical_vnext_native_writes"

SUPPORTED_FINDING_CODES: set[str] = {c.value for c in FindingCode}
SUPPORTED_PROCEDURE_CODES: set[str] = set(FROZEN_RENDERER_PROCEDURE_CODES)

# Mapping legacy condition strings to canonical tooth lifecycles or visual codes
LEGACY_LIFECYCLE_MAP: dict[str, str] = {
    "Missing": ToothLifecycleCode.MISSING.value,
    "Extracted": ToothLifecycleCode.EXTRACTED.value,
    "Impacted": ToothLifecycleCode.IMPACTED.value,
    "Unerupted": ToothLifecycleCode.UNERUPTED.value,
    "Healthy": ToothLifecycleCode.PRESENT.value,
}

LEGACY_FINDING_MAP: dict[str, str] = {
    "Decayed": FindingCode.CARIES.value,
}

LEGACY_PROCEDURE_MAP: dict[str, str] = {
    "Filled": ProcedureCode.REST_COMPOSITE.value,
    "Crown": ProcedureCode.PROS_CROWN.value,
    "RootCanal": ProcedureCode.ENDO_RCT.value,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_datetime(value: Optional[datetime]) -> datetime:
    """Return a timezone-aware UTC value suitable for deterministic comparisons."""
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _has_renderer_supported_target(
    code: str,
    targets: List[schemas.WorkspaceTarget],
) -> bool:
    """Match backend support claims to the frozen odontogram target contract."""
    if code == ProcedureCode.REST_COMPOSITE.value:
        return any(target.kind == "surface" and target.surface_code for target in targets)
    return True


class ClinicalWorkspaceService:
    """Service orchestrating Clinical Workspace Snapshot assembly."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        current_user: Optional[schemas.User] = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user

    async def get_workspace_snapshot(
        self, patient_id: int
    ) -> Optional[schemas.ClinicalWorkspaceSnapshot]:
        """
        Assemble the current versioned Clinical Workspace Snapshot for a patient.
        Missing or cross-tenant patient returns None (router translates to 404).
        """
        patient = await crud.get_patient(self.db, patient_id, self.tenant_id)
        if not patient:
            return None

        # 1. Rollout mode resolution (fail-closed via FeatureFlagService)
        rollout_mode = await self._resolve_rollout_mode()

        # 2. Coverage resolution (domains: teeth, treatments, sessions)
        # Default must never imply COMPLETE (defaults to UNCOVERED).
        coverages = await crud.get_projection_coverages(self.db, patient_id, self.tenant_id)
        coverage_map: Dict[str, str] = {c.domain: c.status for c in coverages}
        coverage: Dict[str, str] = {
            "teeth": coverage_map.get("teeth", "UNCOVERED"),
            "treatments": coverage_map.get("treatments", "UNCOVERED"),
            "sessions": coverage_map.get("sessions", "UNCOVERED"),
        }

        warnings: List[schemas.ClinicalWorkspaceWarning] = []
        has_fallback_truth = False

        # COMPLETE coverage is safe to enforce only after the native command
        # path is enabled. Until then, legacy writes remain authoritative and
        # must continue to contribute without overriding native truth.
        effective_coverage = dict(coverage)
        if rollout_mode == "VNEXT_PRIMARY":
            native_writes_enabled = await FeatureFlagService.is_feature_enabled(
                self.db,
                FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
                self.tenant_id,
            )
            if not native_writes_enabled:
                compatibility_domains = [
                    domain
                    for domain, status in coverage.items()
                    if status == "COMPLETE"
                ]
                for domain in compatibility_domains:
                    effective_coverage[domain] = "PARTIAL"
                if compatibility_domains:
                    warnings.append(
                        schemas.ClinicalWorkspaceWarning(
                            code="LEGACY_WRITE_COMPATIBILITY_ACTIVE",
                            message=(
                                "Legacy clinical writes remain active; COMPLETE domains "
                                "continue accepting deduplicated legacy contributions until "
                                "the native command path is enabled."
                            ),
                            details={"domains": compatibility_domains},
                        )
                    )

        # Initialize full FDI teeth map (52 canonical FDI keys)
        teeth_map: Dict[str, schemas.WorkspaceToothSummary] = {}
        native_teeth_with_truth: set[str] = set()
        native_teeth_status_with_truth: set[str] = set()
        native_covered_procedures: set[tuple[str, str]] = set()
        native_covered_surfaces: set[tuple[str, str, str]] = set()
        work_item_summaries: List[schemas.WorkspaceWorkItemSummary] = []

        initial_provenance = "native" if rollout_mode == "VNEXT_PRIMARY" else "legacy_fallback"
        initial_certainty = "EXACT" if rollout_mode == "VNEXT_PRIMARY" else "UNKNOWN"

        for k in FDI_TOOTH_KEYS:
            teeth_map[k] = schemas.WorkspaceToothSummary(
                tooth_key=k,
                lifecycle=ToothLifecycleCode.PRESENT.value,
                condition=None,
                findings=[],
                procedures=[],
                provenance=initial_provenance,
                temporal_certainty=initial_certainty,
                notes=None,
            )

        # 3. Deterministic Reduction of Native Truth (VNEXT_PRIMARY only)
        # In LEGACY_ONLY and SHADOW rollout modes, the user-visible projection reflects
        # legacy records only. Native truth is not projected into visible teeth or work items.
        if rollout_mode == "VNEXT_PRIMARY":
            work_items = await crud.get_clinical_work_items_for_patient(
                self.db, patient_id, self.tenant_id
            )
            events = await crud.get_clinical_events_for_patient(
                self.db, patient_id, self.tenant_id
            )

            superseded_work_item_ids: set[int] = set()
            active_native_work_items: list[models.ClinicalWorkItem] = []
            for wi in work_items:
                status_lower = (wi.status or "").lower()
                if status_lower in ("superseded", "entered-in-error", "entered_in_error"):
                    superseded_work_item_ids.add(wi.id)
                else:
                    active_native_work_items.append(wi)

            active_native_work_items.sort(
                key=lambda w: (_normalized_datetime(w.created_at), w.id)
            )
            native_work_item_visual_keys = {
                (work_item.id, target.tooth_key, work_item.code)
                for work_item in active_native_work_items
                for target in (work_item.targets or [])
                if (work_item.status or "").lower() != "cancelled"
            }

            active_native_events: list[models.ClinicalEvent] = []
            for ev in events:
                ev_type_lower = (ev.event_type or "").lower()
                payload = ev.payload or {}
                ev_status = str(payload.get("status", "")).lower()
                is_error = bool(payload.get("entered_in_error") or payload.get("superseded"))
                if (
                    ev_type_lower in ("superseded", "entered_in_error", "entered-in-error")
                    or ev_status in ("superseded", "entered-in-error", "entered_in_error")
                    or is_error
                    or (ev.work_item_id and ev.work_item_id in superseded_work_item_ids)
                ):
                    continue
                active_native_events.append(ev)

            active_native_events.sort(
                key=lambda e: (
                    _normalized_datetime(e.occurred_at or e.created_at),
                    _normalized_datetime(e.created_at),
                    e.id,
                )
            )

            # Apply native events to teeth
            latest_lifecycle_event_at: dict[str, datetime] = {}
            for ev in active_native_events:
                ev_targets = getattr(ev, "targets", []) or []
                target_tooth_keys = [t.tooth_key for t in ev_targets if t.tooth_key in teeth_map]

                payload = ev.payload or {}
                event_type = str(ev.event_type or "").lower()
                event_kind = str(payload.get("kind") or "").lower()
                canonical_code = str(payload.get("canonical_code") or "").upper()
                lifecycle_candidate = (
                    payload.get("lifecycle")
                    or (
                        canonical_code
                        if event_type == "tooth_lifecycle_changed" or event_kind == "lifecycle"
                        else None
                    )
                    or ev.event_type
                )
                if isinstance(lifecycle_candidate, str) and lifecycle_candidate.upper() in CANONICAL_TOOTH_LIFECYCLE_CODES:
                    canon_lifecycle = lifecycle_candidate.upper()
                    for tk in target_tooth_keys:
                        native_teeth_with_truth.add(tk)
                        native_teeth_status_with_truth.add(tk)
                        latest_lifecycle_event_at[tk] = _normalized_datetime(
                            ev.occurred_at or ev.created_at
                        )
                        t_summary = teeth_map[tk]
                        t_summary.lifecycle = canon_lifecycle
                        t_summary.provenance = "native"
                        t_summary.temporal_certainty = "EXACT"
                        if canon_lifecycle == ToothLifecycleCode.MISSING.value:
                            t_summary.condition = "Missing"
                        elif canon_lifecycle == ToothLifecycleCode.PRESENT.value:
                            cond_candidate = payload.get("condition")
                            if cond_candidate:
                                t_summary.condition = cond_candidate

                visual_kind = None
                supported_codes: set[str] = set()
                if event_type == "finding_recorded" or event_kind == "finding":
                    visual_kind = "finding"
                    supported_codes = SUPPORTED_FINDING_CODES
                elif event_type == "procedure_recorded" or event_kind == "procedure":
                    visual_kind = "procedure"
                    supported_codes = SUPPORTED_PROCEDURE_CODES

                if visual_kind and canonical_code:
                    if canonical_code not in supported_codes:
                        warnings.append(
                            schemas.ClinicalWorkspaceWarning(
                                code="UNSUPPORTED_CLINICAL_CODE",
                                message=(
                                    f"Unsupported canonical code '{canonical_code}' on "
                                    f"clinical event {ev.id} preserved as an unclassified warning."
                                ),
                                source_kind="clinical_event",
                                source_id=ev.id,
                                raw_value=canonical_code,
                                details={"event_type": ev.event_type, "kind": visual_kind},
                            )
                        )
                        continue

                    workspace_targets = [
                        schemas.WorkspaceTarget(
                            kind=target.target_kind,
                            tooth_key=target.tooth_key,
                            surface_code=target.surface_code,
                            root_id=target.root_id,
                            canal_id=target.canal_id,
                        )
                        for target in ev_targets
                        if target.tooth_key in teeth_map
                    ]
                    if not _has_renderer_supported_target(canonical_code, workspace_targets):
                        warnings.append(
                            schemas.ClinicalWorkspaceWarning(
                                code="UNSUPPORTED_RENDERER_TARGET",
                                message=(
                                    f"Canonical code '{canonical_code}' on clinical event {ev.id} "
                                    "has no target shape supported by the odontogram renderer."
                                ),
                                source_kind="clinical_event",
                                source_id=ev.id,
                                raw_value=canonical_code,
                                details={
                                    "event_type": ev.event_type,
                                    "kind": visual_kind,
                                    "target_kinds": [target.kind for target in workspace_targets],
                                },
                            )
                        )
                        continue
                    visual_entry = schemas.WorkspaceVisualEntry(
                        visual_id=f"ve-ev-{ev.id}",
                        entry_type=visual_kind,
                        code=canonical_code,
                        phase="existing" if visual_kind == "finding" else "completed",
                        targets=workspace_targets,
                        occurred_at=ev.occurred_at,
                        recorded_at=ev.created_at,
                        provenance="native",
                        temporal_certainty="EXACT",
                    )
                    appended_tooth_keys: set[str] = set()
                    for target in workspace_targets:
                        visual_key = (target.tooth_key, canonical_code)
                        linked_visual_key = (
                            ev.work_item_id,
                            target.tooth_key,
                            canonical_code,
                        )
                        if (
                            linked_visual_key in native_work_item_visual_keys
                            or target.tooth_key in appended_tooth_keys
                        ):
                            continue
                        appended_tooth_keys.add(target.tooth_key)
                        native_teeth_with_truth.add(target.tooth_key)
                        native_covered_procedures.add(visual_key)
                        if target.surface_code:
                            native_covered_surfaces.add(
                                (target.tooth_key, target.surface_code, canonical_code)
                            )
                        t_summary = teeth_map[target.tooth_key]
                        t_summary.provenance = "native"
                        t_summary.temporal_certainty = "EXACT"
                        if visual_kind == "finding":
                            t_summary.findings.append(visual_entry)
                            if canonical_code == FindingCode.CARIES.value:
                                t_summary.condition = "Decayed"
                        else:
                            t_summary.procedures.append(visual_entry)
                            if canonical_code == ProcedureCode.REST_COMPOSITE.value:
                                t_summary.condition = "Filled"
                            elif canonical_code == ProcedureCode.PROS_CROWN.value:
                                t_summary.condition = "Crown"
                            elif canonical_code == ProcedureCode.ENDO_RCT.value:
                                t_summary.condition = "RootCanal"

            # Apply native work items to teeth and build work-item summaries
            for wi in active_native_work_items:
                raw_code = wi.code
                is_supported_proc = raw_code in SUPPORTED_PROCEDURE_CODES
                is_supported_find = raw_code in SUPPORTED_FINDING_CODES
                is_supported = is_supported_proc or is_supported_find

                wi_targets = [
                    schemas.WorkspaceTarget(
                        kind=t.target_kind,
                        tooth_key=t.tooth_key,
                        surface_code=t.surface_code,
                        root_id=t.root_id,
                        canal_id=t.canal_id,
                    )
                    for t in (wi.targets or [])
                ]
                has_supported_target = _has_renderer_supported_target(raw_code, wi_targets)
                is_supported = is_supported and has_supported_target

                if not (is_supported_proc or is_supported_find):
                    warnings.append(
                        schemas.ClinicalWorkspaceWarning(
                            code="UNSUPPORTED_CLINICAL_CODE",
                            message=f"Unsupported clinical code '{raw_code}' on work item {wi.id} preserved as unclassified warning.",
                            source_kind="clinical_work_item",
                            source_id=wi.id,
                            raw_value=raw_code,
                            details={"work_item_id": wi.id, "kind": wi.kind, "code": raw_code},
                        )
                    )
                elif not has_supported_target:
                    warnings.append(
                        schemas.ClinicalWorkspaceWarning(
                            code="UNSUPPORTED_RENDERER_TARGET",
                            message=(
                                f"Clinical code '{raw_code}' on work item {wi.id} has no "
                                "target shape supported by the odontogram renderer."
                            ),
                            source_kind="clinical_work_item",
                            source_id=wi.id,
                            raw_value=raw_code,
                            details={
                                "work_item_id": wi.id,
                                "kind": wi.kind,
                                "code": raw_code,
                                "target_kinds": [target.kind for target in wi_targets],
                            },
                        )
                    )

                summary = schemas.WorkspaceWorkItemSummary(
                    id=wi.id,
                    kind=wi.kind,
                    code=raw_code,
                    status=wi.status,
                    notes=wi.notes,
                    targets=wi_targets,
                    provenance="native",
                    recorded_at=wi.created_at,
                    temporal_certainty="EXACT",
                    is_renderer_supported=is_supported,
                )
                work_item_summaries.append(summary)

                if is_supported and wi.status not in ("cancelled",):
                    phase = "completed" if wi.status == "completed" else (
                        "active" if wi.status == "active" else "planned"
                    )
                    entry = schemas.WorkspaceVisualEntry(
                        visual_id=f"ve-wi-{wi.id}",
                        entry_type=wi.kind,
                        code=raw_code,
                        phase=phase,
                        targets=wi_targets,
                        recorded_at=wi.created_at,
                        provenance="native",
                        temporal_certainty="EXACT",
                    )
                    appended_tooth_keys: set[str] = set()
                    for t in wi_targets:
                        native_covered_procedures.add((t.tooth_key, raw_code))
                        if t.surface_code:
                            native_covered_surfaces.add((t.tooth_key, t.surface_code, raw_code))
                        if t.tooth_key in teeth_map and t.tooth_key not in appended_tooth_keys:
                            appended_tooth_keys.add(t.tooth_key)
                            native_teeth_with_truth.add(t.tooth_key)
                            t_summary = teeth_map[t.tooth_key]
                            t_summary.provenance = "native"
                            t_summary.temporal_certainty = "EXACT"
                            if wi.kind == "finding":
                                t_summary.findings.append(entry)
                                if raw_code == FindingCode.CARIES.value:
                                    t_summary.condition = "Decayed"
                            else:
                                t_summary.procedures.append(entry)
                                if raw_code == ProcedureCode.REST_COMPOSITE.value:
                                    t_summary.condition = "Filled"
                                elif raw_code == ProcedureCode.PROS_CROWN.value:
                                    t_summary.condition = "Crown"
                                elif raw_code == ProcedureCode.ENDO_RCT.value:
                                    t_summary.condition = "RootCanal"
                                elif raw_code == ProcedureCode.SURG_EXTRACTION.value and wi.status == "completed":
                                    later_lifecycle_event = latest_lifecycle_event_at.get(t.tooth_key)
                                    if (
                                        later_lifecycle_event is None
                                        or later_lifecycle_event <= _normalized_datetime(wi.created_at)
                                    ):
                                        t_summary.lifecycle = ToothLifecycleCode.EXTRACTED.value
                                        t_summary.condition = "Missing"

        # 4. Fallback or Legacy-Only Contribution
        # When rollout_mode in ("LEGACY_ONLY", "SHADOW"), visible projection is legacy-driven.
        # When rollout_mode == "VNEXT_PRIMARY", native truth wins and legacy contributes ONLY
        # for UNCOVERED or PARTIAL domains, never over COMPLETE native truth.
        legacy_needed = (
            rollout_mode != "VNEXT_PRIMARY"
            or effective_coverage["teeth"] != "COMPLETE"
            or effective_coverage["treatments"] != "COMPLETE"
            or effective_coverage["sessions"] != "COMPLETE"
        )

        if legacy_needed:
            legacy_data = await crud.get_legacy_clinical_records_for_patient(
                self.db, patient_id, self.tenant_id
            )
            verified_patient = VerifiedPatientContext(
                patient_id=patient_id, tenant_id=self.tenant_id
            )
            batch = map_legacy_clinical_batch(
                verified_patient=verified_patient,
                treatments=legacy_data.treatments,
                tooth_statuses=legacy_data.tooth_statuses,
                treatment_sessions=legacy_data.treatment_sessions,
                lab_orders=legacy_data.lab_orders,
            )

            for amb in list(batch.ambiguities) + list(batch.issues):
                warnings.append(
                    schemas.ClinicalWorkspaceWarning(
                        code=amb.code,
                        message=amb.message,
                        source_kind=amb.source_kind,
                        source_id=amb.source_id,
                        raw_value=amb.raw_value,
                        details=dict(amb.details),
                    )
                )

            effective_teeth_cov = "UNCOVERED" if rollout_mode != "VNEXT_PRIMARY" else effective_coverage["teeth"]
            effective_treatments_cov = "UNCOVERED" if rollout_mode != "VNEXT_PRIMARY" else effective_coverage["treatments"]

            # Teeth contribution
            if effective_teeth_cov in ("UNCOVERED", "PARTIAL"):
                for ts in legacy_data.tooth_statuses:
                    raw_tooth = ts.tooth_number
                    tooth_key = str(raw_tooth)
                    if tooth_key not in teeth_map:
                        tooth_key = f"{raw_tooth:02d}" if isinstance(raw_tooth, int) else str(raw_tooth)

                    if tooth_key in teeth_map:
                        if (
                            effective_teeth_cov == "PARTIAL"
                            and tooth_key in native_teeth_status_with_truth
                        ):
                            continue

                        has_fallback_truth = True
                        t_summary = teeth_map[tooth_key]
                        cond = ts.condition
                        t_summary.condition = cond
                        t_summary.provenance = "legacy_fallback"
                        t_summary.temporal_certainty = "UNKNOWN"
                        t_summary.notes = ts.notes

                        if cond and cond in LEGACY_LIFECYCLE_MAP:
                            t_summary.lifecycle = LEGACY_LIFECYCLE_MAP[cond]
                        elif cond and cond in LEGACY_FINDING_MAP:
                            f_code = LEGACY_FINDING_MAP[cond]
                            t_summary.findings.append(
                                schemas.WorkspaceVisualEntry(
                                    visual_id=f"ve-legacy-ts-{ts.id}",
                                    entry_type="finding",
                                    code=f_code,
                                    phase="existing",
                                    targets=[schemas.WorkspaceTarget(kind="tooth", tooth_key=tooth_key)],
                                    provenance="legacy_fallback",
                                    temporal_certainty="UNKNOWN",
                                )
                            )
                        elif cond in LEGACY_PROCEDURE_MAP:
                            p_code = LEGACY_PROCEDURE_MAP[cond]
                            legacy_targets = [
                                schemas.WorkspaceTarget(kind="tooth", tooth_key=tooth_key)
                            ]
                            if _has_renderer_supported_target(p_code, legacy_targets):
                                t_summary.procedures.append(
                                    schemas.WorkspaceVisualEntry(
                                        visual_id=f"ve-legacy-ts-{ts.id}",
                                        entry_type="procedure",
                                        code=p_code,
                                        phase="completed",
                                        targets=legacy_targets,
                                        provenance="legacy_fallback",
                                        temporal_certainty="UNKNOWN",
                                    )
                                )
                            else:
                                warnings.append(
                                    schemas.ClinicalWorkspaceWarning(
                                        code="UNSUPPORTED_RENDERER_TARGET",
                                        message=(
                                            f"Legacy tooth status '{cond}' on tooth {tooth_key} "
                                            "has no target shape supported by the odontogram renderer."
                                        ),
                                        source_kind="tooth_status",
                                        source_id=ts.id,
                                        raw_value=cond,
                                        details={
                                            "tooth_key": tooth_key,
                                            "condition": cond,
                                            "canonical_code": p_code,
                                            "target_kinds": [target.kind for target in legacy_targets],
                                        },
                                    )
                                )
                        else:
                            warnings.append(
                                schemas.ClinicalWorkspaceWarning(
                                    code="UNSUPPORTED_CLINICAL_CODE",
                                    message=f"Unsupported legacy tooth status condition '{cond}' on tooth {tooth_key} preserved as unclassified warning.",
                                    source_kind="tooth_status",
                                    source_id=ts.id,
                                    raw_value=cond,
                                    details={"tooth_key": tooth_key, "condition": cond},
                                )
                            )

            # Treatments contribution
            if effective_treatments_cov in ("UNCOVERED", "PARTIAL"):
                for wi_draft in batch.work_items:
                    if effective_treatments_cov == "PARTIAL":
                        is_covered = False
                        for t in wi_draft.targets:
                            if (t.tooth_key, wi_draft.code) in native_covered_procedures:
                                is_covered = True
                                break
                            if t.surface_code and (t.tooth_key, t.surface_code, wi_draft.code) in native_covered_surfaces:
                                is_covered = True
                                break
                        if is_covered:
                            continue

                    has_fallback_truth = True
                    raw_proc = wi_draft.raw_procedure or wi_draft.code
                    is_supported = (
                        wi_draft.code in SUPPORTED_PROCEDURE_CODES
                        or wi_draft.code in SUPPORTED_FINDING_CODES
                    )

                    fallback_targets = [
                        schemas.WorkspaceTarget(
                            kind=t.target_kind,
                            tooth_key=t.tooth_key,
                            surface_code=t.surface_code,
                            root_id=t.root_id,
                            canal_id=t.canal_id,
                        )
                        for t in wi_draft.targets
                    ]
                    has_supported_target = _has_renderer_supported_target(
                        wi_draft.code,
                        fallback_targets,
                    )
                    is_supported = is_supported and has_supported_target

                    if (
                        wi_draft.code not in SUPPORTED_PROCEDURE_CODES
                        and wi_draft.code not in SUPPORTED_FINDING_CODES
                    ):
                        warnings.append(
                            schemas.ClinicalWorkspaceWarning(
                                code="UNSUPPORTED_CLINICAL_CODE",
                                message=f"Unsupported legacy procedure '{raw_proc}' preserved as unclassified warning.",
                                source_kind="treatment",
                                source_id=wi_draft.source_id,
                                raw_value=raw_proc,
                                details={"source_id": wi_draft.source_id, "procedure": raw_proc},
                            )
                        )
                    elif not has_supported_target:
                        warnings.append(
                            schemas.ClinicalWorkspaceWarning(
                                code="UNSUPPORTED_RENDERER_TARGET",
                                message=(
                                    f"Legacy procedure '{raw_proc}' has no target shape "
                                    "supported by the odontogram renderer."
                                ),
                                source_kind="treatment",
                                source_id=wi_draft.source_id,
                                raw_value=raw_proc,
                                details={
                                    "source_id": wi_draft.source_id,
                                    "procedure": raw_proc,
                                    "canonical_code": wi_draft.code,
                                    "target_kinds": [target.kind for target in fallback_targets],
                                },
                            )
                        )

                    work_item_summaries.append(
                        schemas.WorkspaceWorkItemSummary(
                            id=f"legacy-{wi_draft.source_id}",
                            kind=wi_draft.kind,
                            code=wi_draft.code,
                            status=wi_draft.status,
                            notes=wi_draft.notes,
                            targets=fallback_targets,
                            provenance="legacy_fallback",
                            temporal_certainty="EXACT" if wi_draft.diagnosis else "UNKNOWN",
                            is_renderer_supported=is_supported,
                        )
                    )

                    if is_supported:
                        phase = "completed" if wi_draft.status == "completed" else "planned"
                        ve = schemas.WorkspaceVisualEntry(
                            visual_id=f"ve-legacy-wi-{wi_draft.source_id}",
                            entry_type=wi_draft.kind,
                            code=wi_draft.code,
                            phase=phase,
                            targets=fallback_targets,
                            provenance="legacy_fallback",
                            temporal_certainty="UNKNOWN",
                        )
                        for t in fallback_targets:
                            if t.tooth_key in teeth_map and (
                                effective_treatments_cov == "UNCOVERED"
                                or (
                                    (t.tooth_key, wi_draft.code) not in native_covered_procedures
                                    and (not t.surface_code or (t.tooth_key, t.surface_code, wi_draft.code) not in native_covered_surfaces)
                                )
                            ):
                                t_summary = teeth_map[t.tooth_key]
                                if t.tooth_key not in native_teeth_with_truth:
                                    t_summary.provenance = "legacy_fallback"
                                    t_summary.temporal_certainty = "UNKNOWN"
                                if wi_draft.kind == "finding":
                                    t_summary.findings.append(ve)
                                else:
                                    t_summary.procedures.append(ve)

        if has_fallback_truth:
            if rollout_mode == "VNEXT_PRIMARY":
                fallback_msg = "Clinical workspace contains legacy fallback contributions for uncovered or partial domains."
            elif rollout_mode == "SHADOW":
                fallback_msg = "Clinical workspace is operating in shadow rollout mode; user-visible projection reflects legacy data."
            else:
                fallback_msg = "Clinical workspace is operating in legacy-only rollout mode; user-visible projection reflects legacy data."
            warnings.append(
                schemas.ClinicalWorkspaceWarning(
                    code="FALLBACK_DATA_ACTIVE",
                    message=fallback_msg,
                    details={
                        "coverage": coverage,
                        "effective_coverage": effective_coverage,
                        "rollout_mode": rollout_mode,
                    },
                )
            )

        now = _now()
        snapshot_id = f"cws-{patient_id}-{uuid.uuid4().hex[:12]}"

        return schemas.ClinicalWorkspaceSnapshot(
            projection_id=snapshot_id,
            schema_version=1,
            patient_id=patient_id,
            generated_at=now,
            effective_at=now,
            read_mode=rollout_mode,
            coverage=coverage,
            warnings=warnings,
            teeth=teeth_map,
            work_items=work_item_summaries,
        )

    async def _resolve_rollout_mode(self) -> Literal["LEGACY_ONLY", "SHADOW", "VNEXT_PRIMARY"]:
        """
        Resolve the locked rollout mode using FeatureFlagService:
        Precedence:
        1. Explicit enabled shadow -> SHADOW
        2. Otherwise enabled primary -> VNEXT_PRIMARY
        3. Otherwise fail-closed -> LEGACY_ONLY
        """
        is_shadow = await FeatureFlagService.is_feature_enabled(
            self.db, FEATURE_FLAG_CLINICAL_SHADOW, self.tenant_id
        )
        if is_shadow:
            return "SHADOW"

        is_primary = await FeatureFlagService.is_feature_enabled(
            self.db, FEATURE_FLAG_CLINICAL_PRIMARY, self.tenant_id
        )
        if is_primary:
            return "VNEXT_PRIMARY"

        return "LEGACY_ONLY"
