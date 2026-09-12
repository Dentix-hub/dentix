"""
Clinical Workspace CRUD Operations.

Strictly tenant-scoped queries for Clinical Workspace Snapshot reads and
Clinical Projection Coverage management.
"""

import logging
from typing import NamedTuple, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend import models
from backend.core.tenancy import get_current_tenant_id

logger = logging.getLogger(__name__)


class LegacyClinicalRecords(NamedTuple):
    tooth_statuses: Sequence[models.ToothStatus]
    treatments: Sequence[models.Treatment]
    treatment_sessions: Sequence[models.TreatmentSession]
    lab_orders: Sequence[models.LabOrder]


def _validate_tenant(tenant_id: int) -> None:
    ctx_id = get_current_tenant_id()
    if ctx_id is not None and ctx_id != tenant_id:
        logger.critical(
            "SECURITY ALERT: Tenant Isolation Violation! Context: %s, Requested: %s",
            ctx_id,
            tenant_id,
        )
        raise ValueError("Access Denied: Tenant Isolation Violation")


async def get_projection_coverages(
    db: AsyncSession, patient_id: int, tenant_id: int
) -> Sequence[models.ClinicalProjectionCoverage]:
    """Retrieve all domain coverage records for a patient within the tenant."""
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.ClinicalProjectionCoverage).where(
            models.ClinicalProjectionCoverage.tenant_id == tenant_id,
            models.ClinicalProjectionCoverage.patient_id == patient_id,
        )
    )
    return result.scalars().all()


async def set_projection_coverage(
    db: AsyncSession,
    patient_id: int,
    tenant_id: int,
    domain: str,
    status: str,
    notes: str | None = None,
) -> models.ClinicalProjectionCoverage:
    """Create or update domain coverage status for a patient."""
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.ClinicalProjectionCoverage).where(
            models.ClinicalProjectionCoverage.tenant_id == tenant_id,
            models.ClinicalProjectionCoverage.patient_id == patient_id,
            models.ClinicalProjectionCoverage.domain == domain,
        )
    )
    row = result.scalars().first()
    if row:
        row.status = status
        if notes is not None:
            row.notes = notes
    else:
        row = models.ClinicalProjectionCoverage(
            tenant_id=tenant_id,
            patient_id=patient_id,
            domain=domain,
            status=status,
            notes=notes,
        )
        db.add(row)
    await db.flush()
    return row


async def get_clinical_work_items_for_patient(
    db: AsyncSession, patient_id: int, tenant_id: int
) -> Sequence[models.ClinicalWorkItem]:
    """Retrieve all clinical work items with targets for a patient within the tenant."""
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.ClinicalWorkItem)
        .options(selectinload(models.ClinicalWorkItem.targets))
        .where(
            models.ClinicalWorkItem.tenant_id == tenant_id,
            models.ClinicalWorkItem.patient_id == patient_id,
        )
        .order_by(models.ClinicalWorkItem.id.asc())
    )
    return result.scalars().all()


async def get_clinical_events_for_patient(
    db: AsyncSession, patient_id: int, tenant_id: int
) -> Sequence[models.ClinicalEvent]:
    """Retrieve all append-oriented clinical events with targets for a patient within the tenant."""
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.ClinicalEvent)
        .options(selectinload(models.ClinicalEvent.targets))
        .where(
            models.ClinicalEvent.tenant_id == tenant_id,
            models.ClinicalEvent.patient_id == patient_id,
        )
        .order_by(models.ClinicalEvent.occurred_at.asc(), models.ClinicalEvent.id.asc())
    )
    return result.scalars().all()


async def get_care_sessions_for_patient(
    db: AsyncSession, patient_id: int, tenant_id: int
) -> Sequence[models.CareSession]:
    """Retrieve care sessions with steps for a patient within the tenant."""
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.CareSession)
        .options(selectinload(models.CareSession.steps))
        .where(
            models.CareSession.tenant_id == tenant_id,
            models.CareSession.patient_id == patient_id,
        )
        .order_by(models.CareSession.id.asc())
    )
    return result.scalars().all()


async def get_legacy_clinical_records_for_patient(
    db: AsyncSession, patient_id: int, tenant_id: int
) -> LegacyClinicalRecords:
    """Retrieve legacy clinical records (ToothStatus, Treatment, TreatmentSession, LabOrder) strictly tenant-scoped."""
    _validate_tenant(tenant_id)
    ts_res = await db.execute(
        select(models.ToothStatus).where(
            models.ToothStatus.tenant_id == tenant_id,
            models.ToothStatus.patient_id == patient_id,
        ).order_by(models.ToothStatus.id.asc())
    )
    tooth_statuses = ts_res.scalars().all()

    tr_res = await db.execute(
        select(models.Treatment).where(
            models.Treatment.tenant_id == tenant_id,
            models.Treatment.patient_id == patient_id,
        ).order_by(models.Treatment.id.asc())
    )
    treatments = tr_res.scalars().all()

    treatment_ids = [t.id for t in treatments]
    treatment_sessions: Sequence[models.TreatmentSession] = ()
    if treatment_ids:
        sess_res = await db.execute(
            select(models.TreatmentSession).where(
                models.TreatmentSession.tenant_id == tenant_id,
                models.TreatmentSession.treatment_id.in_(treatment_ids),
            ).order_by(models.TreatmentSession.id.asc())
        )
        treatment_sessions = sess_res.scalars().all()

    lab_res = await db.execute(
        select(models.LabOrder).where(
            models.LabOrder.tenant_id == tenant_id,
            models.LabOrder.patient_id == patient_id,
        ).order_by(models.LabOrder.id.asc())
    )
    lab_orders = lab_res.scalars().all()

    return LegacyClinicalRecords(
        tooth_statuses=tooth_statuses,
        treatments=treatments,
        treatment_sessions=treatment_sessions,
        lab_orders=lab_orders,
    )
