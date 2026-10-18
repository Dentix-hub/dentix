#!/usr/bin/env python3
"""
DENTIX Clinical VNext - Controlled G4 Backfill CLI.

Projects legacy Treatment records into ClinicalWorkItem and ClinicalEvent entities
for Odontogram renderer workspace projection.

Authoritative Rules:
1. Dry-run is the DEFAULT. Writes require explicit --apply.
2. Target tenant is required via --tenant-id <id> (or explicit --all-tenants).
3. Idempotent: re-runs detect existing linkages and create no duplicates.
4. Resumable & batched: chunks records by ID and commits per batch.
5. Preserves legacy rows: NEVER modifies Treatment rows.
6. Tenant-isolated: sets RLS context via RlsContext(tenant_id=...) per tenant.
7. Provenance: marks backfilled events with payload['provenance'] = 'backfill'.
8. Reuses TreatmentService mapping and sync methods (no duplicate logic).
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
import re
import sys
from typing import List, Optional, Sequence

# Ensure repository root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
import backend.core.tenant_scope  # noqa: F401 - Registers ORM tenant loader criteria
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext
from backend.models.clinical_core import FDI_TOOTH_KEYS
from backend.clinical.legacy_mapping import (
    map_legacy_tooth_status,
    map_legacy_treatment_session,
    VerifiedPatientContext,
)
from backend.services.treatment_service import TreatmentService

logger = logging.getLogger("backfill_clinical_work_items")


@dataclass
class TenantBackfillReport:
    """Detailed accounting report for a single tenant backfill execution."""
    tenant_id: int
    is_dry_run: bool
    # Treatment backfill counters (backward-compatible)
    scanned: int = 0
    created: int = 0  # In dry-run: "would create"; in apply: "created"
    already_synced: int = 0
    skipped_soft_deleted: int = 0
    skipped_missing_tooth: int = 0
    skipped_invalid_fdi: int = 0
    skipped_unmapped: int = 0
    batch_count: int = 0
    last_processed_id: int = 0

    # ToothStatus backfill counters (G4-M06)
    tooth_statuses_scanned: int = 0
    tooth_statuses_created: int = 0
    tooth_statuses_already_synced: int = 0
    tooth_statuses_skipped: int = 0

    # TreatmentSession backfill counters (G4-M07)
    sessions_scanned: int = 0
    sessions_created: int = 0
    sessions_already_synced: int = 0
    sessions_skipped: int = 0

    @property
    def total_skipped(self) -> int:
        return (
            self.skipped_soft_deleted
            + self.skipped_missing_tooth
            + self.skipped_invalid_fdi
            + self.skipped_unmapped
        )

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "mode": "DRY_RUN" if self.is_dry_run else "APPLY",
            "scanned": self.scanned,
            "created": self.created,
            "already_synced": self.already_synced,
            "skipped_total": self.total_skipped,
            "skipped_breakdown": {
                "soft_deleted": self.skipped_soft_deleted,
                "missing_tooth": self.skipped_missing_tooth,
                "invalid_fdi": self.skipped_invalid_fdi,
                "unmapped": self.skipped_unmapped,
            },
            "tooth_statuses_scanned": self.tooth_statuses_scanned,
            "tooth_statuses_created": self.tooth_statuses_created,
            "tooth_statuses_already_synced": self.tooth_statuses_already_synced,
            "tooth_statuses_skipped": self.tooth_statuses_skipped,
            "sessions_scanned": self.sessions_scanned,
            "sessions_created": self.sessions_created,
            "sessions_already_synced": self.sessions_already_synced,
            "sessions_skipped": self.sessions_skipped,
            "batch_count": self.batch_count,
            "last_processed_id": self.last_processed_id,
        }

    def format_text(self) -> str:
        mode_str = "DRY-RUN (no changes written; pass --apply to execute)" if self.is_dry_run else "APPLY (writes persisted)"
        created_label = "Would Create:" if self.is_dry_run else "Created:     "
        return (
            f"------------------------------------------------------------\n"
            f"Tenant ID:           {self.tenant_id}\n"
            f"Execution Mode:      {mode_str}\n"
            f"Treatments Scanned:  {self.scanned}\n"
            f"{created_label}        {self.created}\n"
            f"Already Synced:      {self.already_synced}\n"
            f"Skipped (Total):     {self.total_skipped}\n"
            f"  - soft_deleted:    {self.skipped_soft_deleted}\n"
            f"  - missing_tooth:   {self.skipped_missing_tooth}\n"
            f"  - invalid_fdi:     {self.skipped_invalid_fdi}\n"
            f"  - unmapped:        {self.skipped_unmapped}\n"
            f"Tooth Statuses:      scanned={self.tooth_statuses_scanned}, {created_label.strip().lower()}={self.tooth_statuses_created}, synced={self.tooth_statuses_already_synced}, skipped={self.tooth_statuses_skipped}\n"
            f"Sessions:            scanned={self.sessions_scanned}, {created_label.strip().lower()}={self.sessions_created}, synced={self.sessions_already_synced}, skipped={self.sessions_skipped}\n"
            f"Batches Processed:   {self.batch_count}\n"
            f"Last Treatment ID:   {self.last_processed_id}\n"
            f"------------------------------------------------------------"
        )


async def backfill_tenant(
    db: AsyncSession,
    tenant_id: int,
    apply: bool = False,
    batch_size: int = 100,
    after_id: int = 0,
) -> TenantBackfillReport:
    """
    Execute backfill for a single tenant with chunked batch processing and resumability.

    Reuses canonical mapping, lookup, and sync methods from TreatmentService.
    """
    token = set_current_tenant_id(tenant_id)
    try:
        report = TenantBackfillReport(
            tenant_id=tenant_id,
            is_dry_run=not apply,
            last_processed_id=after_id,
        )

        # Mock system user for service attribution (treatment.doctor_id takes precedence)
        system_user = models.User(id=None, username="system_backfill", tenant_id=tenant_id)
        service = TreatmentService(db, tenant_id=tenant_id, current_user=system_user)

        current_after_id = after_id

        while True:
            stmt = (
                select(models.Treatment)
                .where(
                    models.Treatment.tenant_id == tenant_id,
                    models.Treatment.id > current_after_id,
                )
                .execution_options(include_deleted=True)
                .order_by(models.Treatment.id.asc())
                .limit(batch_size)
            )
            result = await db.execute(stmt)
            batch = result.scalars().all()

            if not batch:
                break

            report.batch_count += 1

            for treatment in batch:
                report.scanned += 1
                report.last_processed_id = treatment.id
                current_after_id = treatment.id

                # 1. Skip soft-deleted treatments
                if getattr(treatment, "is_deleted", False):
                    report.skipped_soft_deleted += 1
                    continue

                # 2. Check mapping feasibility and categorise skip reasons before DB lookup
                if not treatment.tooth_number:
                    report.skipped_missing_tooth += 1
                    continue

                tooth_key = str(treatment.tooth_number)
                if tooth_key not in FDI_TOOTH_KEYS:
                    report.skipped_invalid_fdi += 1
                    continue

                mapping = service.map_treatment_to_clinical(treatment)
                if mapping is None:
                    report.skipped_unmapped += 1
                    continue

                # 3. Skip treatments that are already synchronized (idempotency check)
                existing_wi = await service.find_linked_clinical_work_item(
                    treatment_id=treatment.id, patient_id=treatment.patient_id
                )
                if existing_wi is not None and existing_wi.status != "cancelled":
                    report.already_synced += 1
                    continue

                # 4. Valid candidate
                if not apply:
                    report.created += 1  # In dry-run, count as "would create"
                else:
                    await service.sync_legacy_treatment(
                        treatment=treatment,
                        surfaces=treatment.surfaces,
                        provenance="backfill",
                    )
                    report.created += 1

            if apply:
                await db.commit()

            if len(batch) < batch_size:
                break

        # -------------------------------------------------------------
        # Phase 2: ToothStatus -> ClinicalEvent & ClinicalEventTarget (G4-M06)
        # -------------------------------------------------------------
        current_after_ts_id = 0
        while True:
            stmt_ts = (
                select(models.ToothStatus)
                .where(
                    models.ToothStatus.tenant_id == tenant_id,
                    models.ToothStatus.id > current_after_ts_id,
                )
                .order_by(models.ToothStatus.id.asc())
                .limit(batch_size)
            )
            result_ts = await db.execute(stmt_ts)
            ts_batch = result_ts.scalars().all()

            if not ts_batch:
                break

            ts_patient_ids = {ts.patient_id for ts in ts_batch if ts.patient_id}

            synced_ts_ids = set()
            if ts_patient_ids:
                ev_stmt = select(models.ClinicalEvent).where(
                    models.ClinicalEvent.tenant_id == tenant_id,
                    models.ClinicalEvent.patient_id.in_(ts_patient_ids),
                )
                ev_res = await db.execute(ev_stmt)
                for ev in ev_res.scalars().all():
                    if isinstance(ev.payload, dict):
                        tid = ev.payload.get("tooth_status_id") or ev.payload.get("legacy_tooth_status_id")
                        if tid is not None:
                            synced_ts_ids.add(tid)

            for ts in ts_batch:
                report.tooth_statuses_scanned += 1
                current_after_ts_id = ts.id

                if getattr(ts, "is_deleted", False) or not ts.patient_id:
                    report.tooth_statuses_skipped += 1
                    continue

                verified_ctx = VerifiedPatientContext(
                    patient_id=ts.patient_id, tenant_id=tenant_id
                )
                draft, issues = map_legacy_tooth_status(ts, verified_ctx)
                if draft is None:
                    report.tooth_statuses_skipped += 1
                    continue

                if ts.id in synced_ts_ids:
                    report.tooth_statuses_already_synced += 1
                    continue

                if not apply:
                    report.tooth_statuses_created += 1
                else:
                    payload = dict(draft.payload)
                    payload["provenance"] = "backfill"
                    payload["source"] = "legacy_tooth_status"
                    payload["tooth_status_id"] = ts.id
                    payload["legacy_tooth_status_id"] = ts.id

                    occurred_at = datetime.now(timezone.utc)
                    event = models.ClinicalEvent(
                        tenant_id=tenant_id,
                        patient_id=ts.patient_id,
                        work_item_id=None,
                        care_session_id=None,
                        event_type=draft.event_type,
                        occurred_at=occurred_at,
                        actor_user_id=None,
                        payload=payload,
                        notes=ts.notes,
                    )
                    for t in draft.targets:
                        target = models.clinical_core.ClinicalEventTarget(
                            tenant_id=tenant_id,
                            target_kind=t.target_kind,
                            tooth_key=t.tooth_key,
                            surface_code=t.surface_code,
                            root_id=t.root_id,
                            canal_id=t.canal_id,
                        )
                        event.targets.append(target)
                    db.add(event)
                    report.tooth_statuses_created += 1
                    synced_ts_ids.add(ts.id)

            if apply:
                await db.commit()

            if len(ts_batch) < batch_size:
                break

        # -------------------------------------------------------------
        # Phase 3: TreatmentSession -> CareSession (G4-M07)
        # -------------------------------------------------------------
        current_after_sess_id = 0
        while True:
            stmt_sess = (
                select(models.TreatmentSession, models.Treatment)
                .outerjoin(
                    models.Treatment,
                    models.TreatmentSession.treatment_id == models.Treatment.id,
                )
                .where(
                    (models.TreatmentSession.tenant_id == tenant_id)
                    | (
                        models.TreatmentSession.tenant_id.is_(None)
                        & (models.Treatment.tenant_id == tenant_id)
                    ),
                    models.TreatmentSession.id > current_after_sess_id,
                )
                .execution_options(include_deleted=True)
                .order_by(models.TreatmentSession.id.asc())
                .limit(batch_size)
            )
            result_sess = await db.execute(stmt_sess)
            sess_batch = result_sess.all()

            if not sess_batch:
                break

            sess_patient_ids = {
                t.patient_id for _, t in sess_batch if t is not None and t.patient_id
            }

            synced_sess_ids = set()
            if sess_patient_ids:
                cs_stmt = select(models.CareSession).where(
                    models.CareSession.tenant_id == tenant_id,
                    models.CareSession.patient_id.in_(sess_patient_ids),
                )
                cs_res = await db.execute(cs_stmt)
                for cs in cs_res.scalars().all():
                    if cs.notes and "[LEGACY_TREATMENT_SESSION:" in cs.notes:
                        matches = re.findall(r"\[LEGACY_TREATMENT_SESSION:(\d+)\]", cs.notes)
                        for m in matches:
                            synced_sess_ids.add(int(m))

            for session, parent_treatment in sess_batch:
                report.sessions_scanned += 1
                current_after_sess_id = session.id

                if parent_treatment is None or getattr(parent_treatment, "is_deleted", False):
                    report.sessions_skipped += 1
                    continue

                if not parent_treatment.patient_id:
                    report.sessions_skipped += 1
                    continue

                verified_ctx = VerifiedPatientContext(
                    patient_id=parent_treatment.patient_id, tenant_id=tenant_id
                )
                draft, issues = map_legacy_treatment_session(
                    session=session,
                    verified_patient=verified_ctx,
                    parent_treatment=parent_treatment,
                )
                if draft is None:
                    report.sessions_skipped += 1
                    continue

                if session.id in synced_sess_ids:
                    report.sessions_already_synced += 1
                    continue

                if not apply:
                    report.sessions_created += 1
                else:
                    provenance_marker = f"[LEGACY_TREATMENT_SESSION:{session.id}]"
                    session_notes = draft.notes.strip() if draft.notes else ""
                    final_notes = (
                        f"{session_notes}\n{provenance_marker}".strip()
                        if session_notes
                        else provenance_marker
                    )

                    sess_date = draft.session_date
                    if sess_date is not None and sess_date.tzinfo is None:
                        sess_date = sess_date.replace(tzinfo=timezone.utc)
                    elif sess_date is None:
                        sess_date = datetime.now(timezone.utc)

                    care_session = models.CareSession(
                        tenant_id=tenant_id,
                        patient_id=draft.patient_id,
                        status="completed",
                        started_at=sess_date,
                        finished_at=sess_date,
                        provider_user_id=parent_treatment.doctor_id,
                        notes=final_notes,
                    )
                    db.add(care_session)
                    report.sessions_created += 1
                    synced_sess_ids.add(session.id)

            if apply:
                await db.commit()

            if len(sess_batch) < batch_size:
                break

        return report
    finally:
        clear_tenant_context(token)


async def discover_active_tenants(db: AsyncSession) -> List[int]:
    """Retrieve all active, non-deleted tenant IDs for --all-tenants mode."""
    stmt = (
        select(models.Tenant.id)
        .where(
            models.Tenant.is_deleted.is_(False),
            models.Tenant.is_active.is_(True),
        )
        .order_by(models.Tenant.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DENTIX Clinical VNext - Controlled G4 Treatment Backfill CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Dry-run for clinic tenant 1 (default):\n"
            "  python scripts/backfill_clinical_work_items.py --tenant-id 1\n\n"
            "  # Apply writes for clinic tenant 1:\n"
            "  python scripts/backfill_clinical_work_items.py --tenant-id 1 --apply\n\n"
            "  # Resume tenant 1 after treatment ID 500:\n"
            "  python scripts/backfill_clinical_work_items.py --tenant-id 1 --apply --after-id 500\n\n"
            "  # Dry-run across all tenants:\n"
            "  python scripts/backfill_clinical_work_items.py --all-tenants\n"
        ),
    )

    tenant_group = parser.add_mutually_exclusive_group(required=True)
    tenant_group.add_argument(
        "--tenant-id",
        type=int,
        help="Target clinic tenant ID to backfill.",
    )
    tenant_group.add_argument(
        "--all-tenants",
        action="store_true",
        help="Explicitly process all active tenants in sequence.",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Persist writes to database. When omitted, defaults to DRY-RUN mode.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of treatments to process per batch (default: 100).",
    )
    parser.add_argument(
        "--after-id",
        type=int,
        default=0,
        help="Resume checkpoint: process only treatments with id > after_id (default: 0).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results in JSON format.",
    )

    return parser.parse_args(args)


async def async_main(cli_args: Optional[Sequence[str]] = None) -> int:
    args = parse_args(cli_args)

    if args.tenant_id is not None and args.tenant_id <= 0:
        print("[ERROR] --tenant-id must be a positive integer.", file=sys.stderr)
        return 2

    if args.batch_size <= 0:
        print("[ERROR] --batch-size must be greater than 0.", file=sys.stderr)
        return 2

    # Discover target tenants
    target_tenant_ids: List[int] = []
    if args.all_tenants:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as discovery_session:
            target_tenant_ids = await discover_active_tenants(discovery_session)
        if not target_tenant_ids:
            print("[WARN] No active tenants found.", file=sys.stderr)
            return 0
    else:
        target_tenant_ids = [args.tenant_id]

    if not args.json:
        banner_mode = "APPLY (WRITING TO DATABASE)" if args.apply else "DRY-RUN (READ-ONLY)"
        print("=" * 60)
        print("DENTIX Clinical VNext - G4 Treatment Backfill CLI")
        print(f"Mode:       {banner_mode}")
        print(f"Tenants:    {target_tenant_ids}")
        print(f"Batch Size: {args.batch_size}")
        print(f"After ID:   {args.after_id}")
        print("=" * 60)

    reports: List[TenantBackfillReport] = []

    for t_id in target_tenant_ids:
        # Each tenant executes under its own RLS session context
        context = RlsContext(tenant_id=t_id)
        async with AsyncSessionLocal(context=context) as session:
            report = await backfill_tenant(
                db=session,
                tenant_id=t_id,
                apply=args.apply,
                batch_size=args.batch_size,
                after_id=args.after_id,
            )
            reports.append(report)
            if not args.json:
                print(report.format_text())

    if args.json:
        payload = {
            "summary": {
                "apply": args.apply,
                "tenants_count": len(reports),
                "total_scanned": sum(r.scanned for r in reports),
                "total_created": sum(r.created for r in reports),
                "total_already_synced": sum(r.already_synced for r in reports),
                "total_skipped": sum(r.total_skipped for r in reports),
                "total_tooth_statuses_scanned": sum(r.tooth_statuses_scanned for r in reports),
                "total_tooth_statuses_created": sum(r.tooth_statuses_created for r in reports),
                "total_tooth_statuses_already_synced": sum(r.tooth_statuses_already_synced for r in reports),
                "total_tooth_statuses_skipped": sum(r.tooth_statuses_skipped for r in reports),
                "total_sessions_scanned": sum(r.sessions_scanned for r in reports),
                "total_sessions_created": sum(r.sessions_created for r in reports),
                "total_sessions_already_synced": sum(r.sessions_already_synced for r in reports),
                "total_sessions_skipped": sum(r.sessions_skipped for r in reports),
            },
            "tenants": [r.to_dict() for r in reports],
        }
        print(json.dumps(payload, indent=2))
    else:
        print("=" * 60)
        status_word = "Applied" if args.apply else "Would Create"
        print("Backfill Complete:")
        print(f"  Tenants processed:           {len(reports)}")
        print(f"  Treatments Scanned:          {sum(r.scanned for r in reports)}")
        print(f"  Treatments {status_word}:     {sum(r.created for r in reports)}")
        print(f"  Treatments Already Synced:   {sum(r.already_synced for r in reports)}")
        print(f"  Treatments Skipped:          {sum(r.total_skipped for r in reports)}")
        print(f"  Tooth Statuses Scanned:      {sum(r.tooth_statuses_scanned for r in reports)}")
        print(f"  Tooth Statuses {status_word}: {sum(r.tooth_statuses_created for r in reports)}")
        print(f"  Tooth Statuses Synced:       {sum(r.tooth_statuses_already_synced for r in reports)}")
        print(f"  Tooth Statuses Skipped:      {sum(r.tooth_statuses_skipped for r in reports)}")
        print(f"  Sessions Scanned:            {sum(r.sessions_scanned for r in reports)}")
        print(f"  Sessions {status_word}:       {sum(r.sessions_created for r in reports)}")
        print(f"  Sessions Synced:             {sum(r.sessions_already_synced for r in reports)}")
        print(f"  Sessions Skipped:            {sum(r.sessions_skipped for r in reports)}")
        print("=" * 60)

    return 0


def main() -> None:
    exit_code = asyncio.run(async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
