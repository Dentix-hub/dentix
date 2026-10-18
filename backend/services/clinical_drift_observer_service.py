"""
Clinical Drift & Mapping Error Observer Service (G16-M04, G16-M05).

Provides strictly read-only, non-mutating clinical drift and mapping error diagnostics
for super-admins to monitor legacy-vs-native parity during SHADOW soak.

Authoritative Rules:
1. Pure read-only: NEVER mutates any database table (zero inserts, updates, deletes).
   Specifically excludes writing ClinicalProjectionCoverage rows.
2. Tenant-scoped: enforces strict tenant isolation via set_current_tenant_id/clear_tenant_context.
3. Compare legacy models.Treatment (non-deleted, valid FDI tooth) count vs native
   models.ClinicalWorkItem (kind='procedure', non-cancelled, non-corrected) count.
4. Per decision PD01b (2026-10-17), missing ToothStatus-derived native events before S03
   are tracked in a separate category (tooth_status_unbackfilled_count), defined as ToothStatus
   rows for which map_legacy_tooth_status returns a draft (LegacyEventDraft) but no native
   event exists. Rows that fail to map are counted in unmapped_issue_count only.
   TenantClinicalDriftReport.patients_with_drift counts treatment drift only.
5. Tracks mapping issues and ambiguities returned by map_legacy_clinical_batch (G16-M04).
"""

from __future__ import annotations

from typing import List, Optional, Set
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.clinical.legacy_mapping import (
    VerifiedPatientContext,
    map_legacy_clinical_batch,
    map_legacy_tooth_notation,
    map_legacy_tooth_status,
)
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.models.clinical_core import FDI_TOOTH_KEYS


class ClinicalDriftObserverService:
    """Service providing strictly read-only clinical drift and error observability."""

    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        self.db = db

    async def compute_tenant_drift(
        self,
        tenant_id: int,
        limit_patients: int = 500,
        after_patient_id: int = 0,
        db: Optional[AsyncSession] = None,
    ) -> schemas.TenantClinicalDriftReport:
        """
        Compute clinical drift and mapping error metrics for a specific tenant.
        Strictly read-only; zero database writes.
        """
        target_db = db or self.db
        if target_db is None:
            raise ValueError("AsyncSession (db) must be provided to ClinicalDriftObserverService")

        # Set tenant context with guaranteed cleanup
        token = set_current_tenant_id(tenant_id)
        try:
            # 1. Verify tenant existence (404 if missing)
            tenant_stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
            tenant_res = await target_db.execute(tenant_stmt)
            tenant = tenant_res.scalar_one_or_none()
            if not tenant:
                raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

            # 2. Select patients in deterministic order
            patients_stmt = (
                select(models.Patient)
                .where(
                    models.Patient.tenant_id == tenant_id,
                    models.Patient.id > after_patient_id,
                )
                .order_by(models.Patient.id.asc())
                .limit(limit_patients)
            )
            patients_res = await target_db.execute(patients_stmt)
            patients = list(patients_res.scalars().all())

            # Aggregate counters
            patients_scanned = len(patients)
            tenant_patients_with_drift = 0
            total_legacy_procedures = 0
            total_native_procedures = 0
            all_missing_treatment_ids: List[int] = []
            total_unmapped_issues = 0
            total_tooth_status_unbackfilled = 0
            patient_drifts: List[schemas.PatientClinicalDriftItem] = []

            for patient in patients:
                # 3. Fetch patient legacy treatments (non-deleted)
                treatments_stmt = (
                    select(models.Treatment)
                    .where(
                        models.Treatment.tenant_id == tenant_id,
                        models.Treatment.patient_id == patient.id,
                        models.Treatment.is_deleted.is_(False),
                    )
                    .order_by(models.Treatment.id.asc())
                )
                treatments_res = await target_db.execute(treatments_stmt)
                treatments = list(treatments_res.scalars().all())

                # 4. Fetch patient tooth status rows
                ts_stmt = (
                    select(models.ToothStatus)
                    .where(
                        models.ToothStatus.tenant_id == tenant_id,
                        models.ToothStatus.patient_id == patient.id,
                    )
                    .order_by(models.ToothStatus.id.asc())
                )
                ts_res = await target_db.execute(ts_stmt)
                tooth_statuses = list(ts_res.scalars().all())

                # 5. Fetch native clinical work items (procedure kind)
                wi_stmt = (
                    select(models.ClinicalWorkItem)
                    .where(
                        models.ClinicalWorkItem.tenant_id == tenant_id,
                        models.ClinicalWorkItem.patient_id == patient.id,
                        models.ClinicalWorkItem.kind == "procedure",
                    )
                    .order_by(models.ClinicalWorkItem.id.asc())
                )
                wi_res = await target_db.execute(wi_stmt)
                work_items = list(wi_res.scalars().all())

                # Active (non-cancelled, non-corrected) native procedures
                active_native_work_items = [
                    wi
                    for wi in work_items
                    if wi.status not in ("cancelled", "entered_in_error", "superseded")
                ]
                patient_native_procedure_count = len(active_native_work_items)
                active_work_item_ids: Set[int] = {wi.id for wi in active_native_work_items}

                # 6. Fetch native clinical events with targets
                events_stmt = (
                    select(models.ClinicalEvent)
                    .options(selectinload(models.ClinicalEvent.targets))
                    .where(
                        models.ClinicalEvent.tenant_id == tenant_id,
                        models.ClinicalEvent.patient_id == patient.id,
                    )
                    .order_by(models.ClinicalEvent.id.asc())
                )
                events_res = await target_db.execute(events_stmt)
                events = list(events_res.scalars().all())

                # Build set of treatments linked to active native work items
                linked_treatment_ids: Set[int] = set()
                for ev in events:
                    if isinstance(ev.payload, dict) and ev.work_item_id in active_work_item_ids:
                        t_id = ev.payload.get("treatment_id") or ev.payload.get("legacy_treatment_id")
                        if t_id is not None:
                            try:
                                linked_treatment_ids.add(int(t_id))
                            except (ValueError, TypeError):
                                pass

                # 7. Map legacy clinical records for error monitoring (G16-M04)
                verified_ctx = VerifiedPatientContext(patient_id=patient.id, tenant_id=tenant_id)
                batch_res = map_legacy_clinical_batch(
                    verified_ctx,
                    treatments=treatments,
                    tooth_statuses=tooth_statuses,
                )
                patient_unmapped_issue_count = len(batch_res.issues) + len(batch_res.ambiguities)

                # 8. Evaluate legacy procedures and missing in native
                patient_legacy_procedure_count = 0
                patient_missing_treatment_ids: List[int] = []

                for t in treatments:
                    # Valid FDI tooth notation requirement
                    tooth_key, _ = map_legacy_tooth_notation(t.tooth_number)
                    if tooth_key is not None and str(tooth_key) in FDI_TOOTH_KEYS:
                        patient_legacy_procedure_count += 1
                        if t.id not in linked_treatment_ids:
                            patient_missing_treatment_ids.append(t.id)

                # 9. Evaluate ToothStatus unbackfilled count per PD01b
                patient_ts_unbackfilled_count = 0
                for ts in tooth_statuses:
                    draft, _ = map_legacy_tooth_status(ts, verified_ctx)
                    if draft is not None:
                        # Draft successfully created. Check if native ClinicalEvent exists
                        has_native_event = False
                        canonical_code = draft.payload.get("canonical_code")
                        draft_tooth_key = draft.targets[0].tooth_key if draft.targets else None

                        for ev in events:
                            if not isinstance(ev.payload, dict):
                                continue
                            # Direct linkage
                            if (
                                ev.payload.get("legacy_tooth_status_id") == ts.id
                                or ev.payload.get("tooth_status_id") == ts.id
                            ):
                                has_native_event = True
                                break
                            # Semantic target & code match
                            if (
                                canonical_code is not None
                                and ev.payload.get("canonical_code") == canonical_code
                                and ev.event_type == draft.event_type
                            ):
                                target_tooth_keys = {
                                    tgt.tooth_key
                                    for tgt in getattr(ev, "targets", [])
                                    if getattr(tgt, "tooth_key", None)
                                }
                                if draft_tooth_key and draft_tooth_key in target_tooth_keys:
                                    has_native_event = True
                                    break

                        if not has_native_event:
                            patient_ts_unbackfilled_count += 1

                # 10. Treatment drift check (PD01b: patients_with_drift counts treatment drift only)
                has_treatment_drift = (
                    len(patient_missing_treatment_ids) > 0
                    or patient_legacy_procedure_count != patient_native_procedure_count
                )
                if has_treatment_drift:
                    tenant_patients_with_drift += 1

                # Include in patient_drifts if any drift or diagnostic issue exists
                if (
                    has_treatment_drift
                    or patient_ts_unbackfilled_count > 0
                    or patient_unmapped_issue_count > 0
                ):
                    patient_drifts.append(
                        schemas.PatientClinicalDriftItem(
                            patient_id=patient.id,
                            legacy_procedure_count=patient_legacy_procedure_count,
                            native_procedure_count=patient_native_procedure_count,
                            missing_treatment_ids=patient_missing_treatment_ids,
                            unmapped_issue_count=patient_unmapped_issue_count,
                            tooth_status_unbackfilled_count=patient_ts_unbackfilled_count,
                            has_drift=has_treatment_drift,
                        )
                    )

                # Tenant totals
                total_legacy_procedures += patient_legacy_procedure_count
                total_native_procedures += patient_native_procedure_count
                all_missing_treatment_ids.extend(patient_missing_treatment_ids)
                total_unmapped_issues += patient_unmapped_issue_count
                total_tooth_status_unbackfilled += patient_ts_unbackfilled_count

            return schemas.TenantClinicalDriftReport(
                tenant_id=tenant_id,
                patients_scanned=patients_scanned,
                patients_with_drift=tenant_patients_with_drift,
                legacy_procedure_count=total_legacy_procedures,
                native_procedure_count=total_native_procedures,
                missing_in_native_treatment_ids=all_missing_treatment_ids,
                unmapped_issue_count=total_unmapped_issues,
                tooth_status_unbackfilled_count=total_tooth_status_unbackfilled,
                patient_drifts=patient_drifts,
            )
        finally:
            clear_tenant_context(token)

    @classmethod
    async def compute_tenant_drift_for_tenant(
        cls,
        db: AsyncSession,
        tenant_id: int,
        limit_patients: int = 500,
        after_patient_id: int = 0,
    ) -> schemas.TenantClinicalDriftReport:
        """Classmethod convenience helper for service invocation."""
        return await cls(db).compute_tenant_drift(
            tenant_id=tenant_id,
            limit_patients=limit_patients,
            after_patient_id=after_patient_id,
        )
