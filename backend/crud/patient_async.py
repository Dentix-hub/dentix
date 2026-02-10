"""
Async Patient CRUD Operations

Mirrors the synchronous patient.py CRUD but uses AsyncSession and SQLAlchemy 2.0 patterns.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from backend import models, schemas
from backend.core.tenancy import get_current_tenant_id


def _validate_tenant(tenant_id: int):
    """Validate tenant isolation."""
    ctx_id = get_current_tenant_id()
    if ctx_id is not None and ctx_id != tenant_id:
        raise ValueError("Access Denied: Tenant Isolation Violation")


# --- Patient CRUD ---
async def get_patient(db: AsyncSession, patient_id: int, tenant_id: int):
    """Get a single patient by ID with tenant isolation."""
    _validate_tenant(tenant_id)
    stmt = select(models.Patient).where(
        models.Patient.id == patient_id, models.Patient.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_patients(
    db: AsyncSession, tenant_id: int, skip: int = 0, limit: int = 100
):
    """Get all patients for a tenant with pagination."""
    _validate_tenant(tenant_id)
    stmt = (
        select(models.Patient)
        .where(models.Patient.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def search_patients(db: AsyncSession, query: str, tenant_id: int):
    """Search patients by name, phone, or address."""
    search = f"%{query}%"
    stmt = (
        select(models.Patient)
        .where(
            models.Patient.tenant_id == tenant_id,
            or_(
                models.Patient.name.ilike(search),
                models.Patient.phone.ilike(search),
                models.Patient.address.ilike(search),
            ),
        )
        .limit(5)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_patient(
    db: AsyncSession, patient: schemas.PatientCreate, tenant_id: int
):
    """Create a new patient."""
    db_patient = models.Patient(**patient.model_dump(), tenant_id=tenant_id)
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)
    return db_patient


async def update_patient(
    db: AsyncSession, patient_id: int, patient: schemas.PatientCreate, tenant_id: int
):
    """Update an existing patient."""
    db_patient = await get_patient(db, patient_id, tenant_id)
    if db_patient:
        for key, value in patient.model_dump().items():
            setattr(db_patient, key, value)
        await db.commit()
        await db.refresh(db_patient)
    return db_patient


async def delete_patient(db: AsyncSession, patient_id: int, tenant_id: int):
    """Delete a patient."""
    db_patient = await get_patient(db, patient_id, tenant_id)
    if db_patient:
        await db.delete(db_patient)
        await db.commit()
    return db_patient


# --- Tooth Status CRUD ---
async def get_tooth_status(db: AsyncSession, patient_id: int, tenant_id: int):
    """Get all tooth statuses for a patient."""
    stmt = (
        select(models.ToothStatus)
        .join(models.Patient)
        .where(
            models.ToothStatus.patient_id == patient_id,
            models.Patient.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_tooth_status(
    db: AsyncSession, status: schemas.ToothStatusCreate, tenant_id: int
):
    """Create or update a tooth status."""
    stmt = (
        select(models.ToothStatus)
        .join(models.Patient)
        .where(
            models.ToothStatus.patient_id == status.patient_id,
            models.ToothStatus.tooth_number == status.tooth_number,
            models.Patient.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    db_status = result.scalar_one_or_none()

    if db_status:
        db_status.condition = status.condition
        db_status.notes = status.notes
    else:
        db_status = models.ToothStatus(**status.model_dump())
        db.add(db_status)

    await db.commit()
    await db.refresh(db_status)
    return db_status


# --- Attachments ---
async def create_attachment(db: AsyncSession, attachment: schemas.AttachmentCreate):
    """Create a new attachment."""
    db_attachment = models.Attachment(**attachment.model_dump())
    db.add(db_attachment)
    await db.commit()
    await db.refresh(db_attachment)
    return db_attachment


async def get_patient_attachments(db: AsyncSession, patient_id: int, tenant_id: int):
    """Get all attachments for a patient."""
    stmt = (
        select(models.Attachment)
        .join(models.Patient)
        .where(
            models.Attachment.patient_id == patient_id,
            models.Patient.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def delete_attachment(db: AsyncSession, attachment_id: int, tenant_id: int):
    """Delete an attachment."""
    stmt = (
        select(models.Attachment)
        .join(models.Patient)
        .where(
            models.Attachment.id == attachment_id, models.Patient.tenant_id == tenant_id
        )
    )
    result = await db.execute(stmt)
    attachment = result.scalar_one_or_none()
    if attachment:
        await db.delete(attachment)
        await db.commit()
    return attachment


# --- Prescriptions ---
async def create_prescription(
    db: AsyncSession, prescription: schemas.PrescriptionCreate
):
    """Create a new prescription."""
    db_prescription = models.Prescription(**prescription.model_dump())
    db.add(db_prescription)
    await db.commit()
    await db.refresh(db_prescription)
    return db_prescription


async def get_prescriptions(db: AsyncSession, patient_id: int, tenant_id: int):
    """Get all prescriptions for a patient."""
    stmt = (
        select(models.Prescription)
        .join(models.Patient)
        .where(
            models.Prescription.patient_id == patient_id,
            models.Patient.tenant_id == tenant_id,
        )
        .order_by(models.Prescription.date.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def delete_prescription(db: AsyncSession, prescription_id: int, tenant_id: int):
    """Delete a prescription."""
    stmt = (
        select(models.Prescription)
        .join(models.Patient)
        .where(
            models.Prescription.id == prescription_id,
            models.Patient.tenant_id == tenant_id,
        )
    )
    result = await db.execute(stmt)
    db_prescription = result.scalar_one_or_none()
    if db_prescription:
        await db.delete(db_prescription)
        await db.commit()
    return db_prescription
