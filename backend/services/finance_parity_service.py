"""
Finance Parity and Shadow Calculator Service (G14-M06, G14-M07, G14-M08).

Provides strictly read-only, non-mutating financial comparison between
authoritative legacy finance (Treatment and Payment) and shadow VNext finance
(ClinicalCharge and work-item billing projection).

Authoritative Rules:
1. Pure read-only: NEVER mutates any database table (zero inserts, updates, deletes).
2. Tenant-scoped: enforces strict tenant isolation via set_current_tenant_id/clear_tenant_context.
3. Compare legacy net charges SUM(Treatment.cost - Treatment.discount) vs
   shadow VNext charges (active ClinicalCharge + backfilled work-item fee projection).
4. Payments are unchanged (G14-M05): payments_total is identical between legacy and shadow.
5. All monetary calculations use Decimal with 2 decimal places to guarantee mathematical accuracy.
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.models.clinical_core import (
    CLINICAL_CHARGE_STATUS_VOIDED,
)

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal("0.01")


def _quantize(val: Any) -> Decimal:
    """Quantize an incoming number/float/Decimal/None to 2 decimal places."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    try:
        return Decimal(str(val)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


class FinanceParityService:
    """Service providing strictly read-only financial parity calculations."""

    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        self.db = db

    async def compute_patient_parity(
        self,
        tenant_id: int,
        patient_id: int,
        db: Optional[AsyncSession] = None,
    ) -> schemas.PatientFinanceParityDetail:
        """
        Compute financial parity for a specific patient.
        Compares legacy treatments against shadow VNext charges and projection.
        Strictly read-only; zero database writes.
        """
        target_db = db or self.db
        if target_db is None:
            raise ValueError("AsyncSession (db) must be provided to FinanceParityService")

        token = set_current_tenant_id(tenant_id)
        try:
            # 1. Verify tenant exists (404 if missing)
            tenant_stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
            tenant_res = await target_db.execute(tenant_stmt)
            tenant = tenant_res.scalar_one_or_none()
            if not tenant:
                raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

            # 2. Verify patient exists in tenant (404 if missing or belongs to another tenant)
            patient_stmt = select(models.Patient).where(
                models.Patient.id == patient_id,
                models.Patient.tenant_id == tenant_id,
            )
            patient_res = await target_db.execute(patient_stmt)
            patient = patient_res.scalar_one_or_none()
            if not patient:
                raise HTTPException(
                    status_code=404,
                    detail=f"Patient {patient_id} not found in tenant {tenant_id}",
                )

            now = datetime.now(timezone.utc)
            detail = await self._calculate_patient_parity_internal(
                target_db=target_db,
                tenant_id=tenant_id,
                patient=patient,
                evaluated_at=now,
                include_breakdown=True,
            )
            return detail
        finally:
            clear_tenant_context(token)

    async def compute_tenant_parity(
        self,
        tenant_id: int,
        limit_patients: int = 100,
        after_patient_id: int = 0,
        discrepancies_only: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> schemas.TenantFinanceParityReport:
        """
        Compute aggregated financial parity metrics for a tenant across patients.
        Strictly read-only; zero database writes.
        """
        target_db = db or self.db
        if target_db is None:
            raise ValueError("AsyncSession (db) must be provided to FinanceParityService")

        token = set_current_tenant_id(tenant_id)
        try:
            # 1. Verify tenant exists (404 if missing)
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

            now = datetime.now(timezone.utc)

            total_legacy_charges = Decimal("0.00")
            total_shadow_charges = Decimal("0.00")
            total_charge_delta = Decimal("0.00")
            total_payments = Decimal("0.00")
            total_legacy_balance = Decimal("0.00")
            total_shadow_balance = Decimal("0.00")
            total_balance_delta = Decimal("0.00")

            patients_with_parity = 0
            patients_with_discrepancy = 0
            patient_summaries: List[schemas.PatientFinanceParitySummary] = []

            for patient in patients:
                summary = await self._calculate_patient_parity_internal(
                    target_db=target_db,
                    tenant_id=tenant_id,
                    patient=patient,
                    evaluated_at=now,
                    include_breakdown=False,
                )

                total_legacy_charges += summary.legacy_charges
                total_shadow_charges += summary.shadow_charges
                total_charge_delta += summary.charge_delta
                total_payments += summary.payments_total
                total_legacy_balance += summary.legacy_balance
                total_shadow_balance += summary.shadow_balance
                total_balance_delta += summary.balance_delta

                if summary.is_parity_match:
                    patients_with_parity += 1
                else:
                    patients_with_discrepancy += 1

                if not discrepancies_only or not summary.is_parity_match:
                    patient_summaries.append(
                        schemas.PatientFinanceParitySummary(
                            patient_id=summary.patient_id,
                            patient_name=summary.patient_name,
                            legacy_charges=summary.legacy_charges,
                            shadow_charges=summary.shadow_charges,
                            charge_delta=summary.charge_delta,
                            payments_total=summary.payments_total,
                            legacy_balance=summary.legacy_balance,
                            shadow_balance=summary.shadow_balance,
                            balance_delta=summary.balance_delta,
                            is_parity_match=summary.is_parity_match,
                            status=summary.status,
                            legacy_treatments_count=summary.legacy_treatments_count,
                            clinical_charges_count=summary.clinical_charges_count,
                            work_items_count=summary.work_items_count,
                            discrepancy_reasons=summary.discrepancy_reasons,
                        )
                    )

            is_tenant_parity_match = (patients_with_discrepancy == 0)

            return schemas.TenantFinanceParityReport(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                evaluated_at=now,
                total_patients_evaluated=len(patients),
                patients_with_parity=patients_with_parity,
                patients_with_discrepancy=patients_with_discrepancy,
                is_tenant_parity_match=is_tenant_parity_match,
                total_legacy_charges=_quantize(total_legacy_charges),
                total_shadow_charges=_quantize(total_shadow_charges),
                total_charge_delta=_quantize(total_charge_delta),
                total_payments=_quantize(total_payments),
                total_legacy_balance=_quantize(total_legacy_balance),
                total_shadow_balance=_quantize(total_shadow_balance),
                total_balance_delta=_quantize(total_balance_delta),
                patients=patient_summaries,
            )
        finally:
            clear_tenant_context(token)

    async def _calculate_patient_parity_internal(
        self,
        target_db: AsyncSession,
        tenant_id: int,
        patient: models.Patient,
        evaluated_at: datetime,
        include_breakdown: bool = False,
    ) -> schemas.PatientFinanceParityDetail:
        """Internal worker to compute single patient parity with/without breakdown."""
        # 1. Fetch non-deleted legacy treatments
        stmt_treatments = (
            select(models.Treatment)
            .where(
                models.Treatment.tenant_id == tenant_id,
                models.Treatment.patient_id == patient.id,
                models.Treatment.is_deleted == False,  # noqa: E712
            )
            .order_by(models.Treatment.id.asc())
        )
        treatments = list((await target_db.execute(stmt_treatments)).scalars().all())

        # 2. Fetch payments
        stmt_payments = (
            select(models.Payment)
            .where(
                models.Payment.tenant_id == tenant_id,
                models.Payment.patient_id == patient.id,
            )
            .order_by(models.Payment.id.asc())
        )
        payments = list((await target_db.execute(stmt_payments)).scalars().all())

        # 3. Fetch clinical work items
        stmt_wi = (
            select(models.ClinicalWorkItem)
            .where(
                models.ClinicalWorkItem.tenant_id == tenant_id,
                models.ClinicalWorkItem.patient_id == patient.id,
            )
            .order_by(models.ClinicalWorkItem.id.asc())
        )
        work_items = list((await target_db.execute(stmt_wi)).scalars().all())

        # 4. Fetch clinical charges
        stmt_charges = (
            select(models.ClinicalCharge)
            .where(
                models.ClinicalCharge.tenant_id == tenant_id,
                models.ClinicalCharge.patient_id == patient.id,
            )
            .order_by(models.ClinicalCharge.id.asc())
        )
        charges = list((await target_db.execute(stmt_charges)).scalars().all())

        # 5. Fetch clinical events for work items to find legacy treatment linkages
        wi_ids = [w.id for w in work_items]
        events: List[models.ClinicalEvent] = []
        if wi_ids:
            stmt_events = (
                select(models.ClinicalEvent)
                .where(
                    models.ClinicalEvent.tenant_id == tenant_id,
                    models.ClinicalEvent.patient_id == patient.id,
                    models.ClinicalEvent.work_item_id.in_(wi_ids),
                )
                .order_by(models.ClinicalEvent.id.asc())
            )
            events = list((await target_db.execute(stmt_events)).scalars().all())

        # Map work_item_id -> legacy_treatment_id
        wi_to_treatment_id: Dict[int, int] = {}
        treatment_id_to_wi_id: Dict[int, int] = {}
        for ev in events:
            if isinstance(ev.payload, dict):
                t_id = ev.payload.get("treatment_id") or ev.payload.get("legacy_treatment_id")
                if t_id is not None:
                    try:
                        int_t_id = int(t_id)
                        wi_to_treatment_id[ev.work_item_id] = int_t_id
                        treatment_id_to_wi_id[int_t_id] = ev.work_item_id
                    except (ValueError, TypeError):
                        pass

        # Map work_item_id -> ClinicalCharge (active non-voided preferred)
        charges_by_wi: Dict[int, models.ClinicalCharge] = {}
        active_charges: List[models.ClinicalCharge] = []
        for c in charges:
            if c.status != CLINICAL_CHARGE_STATUS_VOIDED:
                active_charges.append(c)
                charges_by_wi[c.work_item_id] = c

        # --- Legacy Calculation ---
        legacy_charges = Decimal("0.00")
        legacy_treatments_breakdown: List[Dict[str, Any]] = []
        for t in treatments:
            t_cost = _quantize(t.cost)
            t_disc = _quantize(t.discount)
            t_net = _quantize(t_cost - t_disc)
            legacy_charges += t_net
            if include_breakdown:
                legacy_treatments_breakdown.append({
                    "id": t.id,
                    "procedure": t.procedure,
                    "tooth_number": t.tooth_number,
                    "cost": float(t_cost),
                    "discount": float(t_disc),
                    "net": float(t_net),
                    "status": t.status,
                    "date": t.date.isoformat() if t.date else None,
                    "linked_work_item_id": treatment_id_to_wi_id.get(t.id),
                })

        # --- Payments Calculation ---
        payments_total = Decimal("0.00")
        for p in payments:
            payments_total += _quantize(p.amount)

        legacy_balance = _quantize(legacy_charges - payments_total)

        # --- Shadow VNext Calculation ---
        # Shadow charges come from:
        # A) Active ClinicalCharges (created natively)
        # B) Completed procedure work items that are legacy-synced (taking net cost from legacy treatment)
        shadow_charges = Decimal("0.00")
        work_item_projections: List[Dict[str, Any]] = []
        clinical_charges_breakdown: List[Dict[str, Any]] = []

        # Map treatments by id
        treatments_by_id = {t.id: t for t in treatments}

        # Track linked legacy treatments to avoid double counting
        accounted_treatment_ids: set[int] = set()

        for wi in work_items:
            tx_id = wi_to_treatment_id.get(wi.id)
            tx = treatments_by_id.get(tx_id) if tx_id else None
            ch = charges_by_wi.get(wi.id)

            if tx is not None:
                accounted_treatment_ids.add(tx.id)
                t_cost = _quantize(tx.cost)
                t_disc = _quantize(tx.discount)
                t_net = _quantize(t_cost - t_disc)
                shadow_charges += t_net
                if include_breakdown:
                    work_item_projections.append({
                        "work_item_id": wi.id,
                        "kind": wi.kind,
                        "code": wi.code,
                        "work_item_status": wi.status,
                        "source": "legacy_treatment",
                        "amount": float(t_cost),
                        "discount": float(t_disc),
                        "net": float(t_net),
                        "status": tx.status,
                        "charge_id": None,
                        "treatment_id": tx.id,
                    })
            elif ch is not None:
                ch_amt = _quantize(ch.amount)
                ch_disc = _quantize(ch.discount)
                ch_net = _quantize(ch_amt - ch_disc)
                shadow_charges += ch_net
                if include_breakdown:
                    work_item_projections.append({
                        "work_item_id": wi.id,
                        "kind": wi.kind,
                        "code": wi.code,
                        "work_item_status": wi.status,
                        "source": "clinical_charge",
                        "amount": float(ch_amt),
                        "discount": float(ch_disc),
                        "net": float(ch_net),
                        "status": ch.status,
                        "charge_id": ch.id,
                        "treatment_id": None,
                    })
            else:
                if include_breakdown:
                    work_item_projections.append({
                        "work_item_id": wi.id,
                        "kind": wi.kind,
                        "code": wi.code,
                        "work_item_status": wi.status,
                        "source": "none",
                        "amount": 0.0,
                        "discount": 0.0,
                        "net": 0.0,
                        "status": None,
                        "charge_id": None,
                        "treatment_id": None,
                    })

        if include_breakdown:
            for c in charges:
                c_amt = _quantize(c.amount)
                c_disc = _quantize(c.discount)
                c_net = _quantize(c_amt - c_disc)
                clinical_charges_breakdown.append({
                    "id": c.id,
                    "work_item_id": c.work_item_id,
                    "care_session_id": c.care_session_id,
                    "doctor_id": c.doctor_id,
                    "amount": float(c_amt),
                    "discount": float(c_disc),
                    "net": float(c_net),
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })

        shadow_balance = _quantize(shadow_charges - payments_total)
        charge_delta = _quantize(shadow_charges - legacy_charges)
        balance_delta = _quantize(shadow_balance - legacy_balance)

        is_parity_match = (abs(charge_delta) < Decimal("0.005"))

        # Status and Discrepancies
        discrepancy_reasons: List[str] = []
        if is_parity_match:
            status = "PARITY_MATCH"
        elif charge_delta > 0:
            status = "SHADOW_SURPLUS"
        else:
            status = "LEGACY_SURPLUS"

        # Discrepancy diagnosis
        unlinked_treatments = [t for t in treatments if t.id not in accounted_treatment_ids]
        if unlinked_treatments:
            unlinked_sum = sum(_quantize(t.cost - (t.discount or 0)) for t in unlinked_treatments)
            discrepancy_reasons.append(
                f"{len(unlinked_treatments)} legacy treatment(s) unlinked to work items (total net: {unlinked_sum})"
            )

        native_charges_count = len([c for c in active_charges if c.work_item_id not in wi_to_treatment_id])
        if native_charges_count > 0:
            native_sum = sum(
                _quantize(c.amount - (c.discount or 0))
                for c in active_charges
                if c.work_item_id not in wi_to_treatment_id
            )
            discrepancy_reasons.append(
                f"{native_charges_count} native clinical charge(s) not in legacy treatments (total net: {native_sum})"
            )

        unbilled_completed_wi = [
            wi for wi in work_items
            if wi.kind == "procedure"
            and wi.status == "completed"
            and wi.id not in wi_to_treatment_id
            and wi.id not in charges_by_wi
        ]
        if unbilled_completed_wi:
            discrepancy_reasons.append(
                f"{len(unbilled_completed_wi)} completed procedure(s) have no charge or treatment"
            )

        return schemas.PatientFinanceParityDetail(
            patient_id=patient.id,
            patient_name=patient.name,
            tenant_id=tenant_id,
            evaluated_at=evaluated_at,
            legacy_charges=_quantize(legacy_charges),
            shadow_charges=_quantize(shadow_charges),
            charge_delta=_quantize(charge_delta),
            payments_total=_quantize(payments_total),
            legacy_balance=_quantize(legacy_balance),
            shadow_balance=_quantize(shadow_balance),
            balance_delta=_quantize(balance_delta),
            is_parity_match=is_parity_match,
            status=status,
            legacy_treatments_count=len(treatments),
            clinical_charges_count=len(active_charges),
            work_items_count=len(work_items),
            discrepancy_reasons=discrepancy_reasons,
            work_item_projections=work_item_projections,
            clinical_charges=clinical_charges_breakdown,
            legacy_treatments=legacy_treatments_breakdown,
        )
