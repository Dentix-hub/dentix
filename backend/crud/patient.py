import logging
from sqlalchemy import select
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas
from backend.core.tenancy import get_current_tenant_id

logger = logging.getLogger(__name__)


def _validate_tenant(tenant_id: int):
    ctx_id = get_current_tenant_id()
    if ctx_id is not None and ctx_id != tenant_id:
        logger.critical(
            "SECURITY ALERT: Tenant Isolation Violation! Context: %s, Requested: %s",
            ctx_id, tenant_id,
        )
        raise ValueError("Access Denied: Tenant Isolation Violation")


async def get_patient(db: AsyncSession, patient_id: int, tenant_id: int):
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.Patient).where(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,
        )
    )
    return result.scalars().first()


async def get_patients(db: AsyncSession, tenant_id: int, skip: int = 0, limit: int = 100):
    _validate_tenant(tenant_id)
    stmt = (
        select(models.Patient)
        .where(models.Patient.tenant_id == tenant_id, models.Patient.is_deleted == False)
        .options(load_only(
            models.Patient.id, models.Patient.name, models.Patient.phone, models.Patient.email,
            models.Patient.age, models.Patient.created_at, models.Patient.assigned_doctor_id,
        ))
        .options(joinedload(models.Patient.assigned_doctor))
        .order_by(models.Patient.created_at.desc())
        .offset(skip).limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def search_patients(db: AsyncSession, query: str, tenant_id: int):
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.Patient).where(
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,
            models.Patient.name.ilike(f"%{query}%"),
        ).limit(5)
    )
    return result.scalars().all()


async def create_patient(db: AsyncSession, patient: schemas.PatientCreate, tenant_id: int):
    _validate_tenant(tenant_id)
    patient_data = patient.dict()
    patient_data.pop("gender", None)
    db_patient = models.Patient(**patient_data, tenant_id=tenant_id)
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)
    return db_patient


async def update_patient(db: AsyncSession, patient_id: int, patient: schemas.PatientCreate, tenant_id: int):
    db_patient = await get_patient(db, patient_id, tenant_id)
    if db_patient:
        for key, value in patient.dict().items():
            setattr(db_patient, key, value)
        await db.commit()
        await db.refresh(db_patient)
    return db_patient


async def delete_patient(db: AsyncSession, patient_id: int, tenant_id: int):
    from datetime import datetime, timezone
    db_patient = await get_patient(db, patient_id, tenant_id)
    if db_patient:
        db_patient.is_deleted = True
        db_patient.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_patient)
    return db_patient


async def delete_patient_permanently(db: AsyncSession, patient_id: int, tenant_id: int):
    db_patient = await get_patient(db, patient_id, tenant_id)
    if not db_patient:
        result = await db.execute(
            select(models.Patient).where(
                models.Patient.id == patient_id, models.Patient.tenant_id == tenant_id,
            )
        )
        db_patient = result.scalars().first()
    if db_patient:
        await db.delete(db_patient)
        await db.commit()
    return db_patient


async def get_tooth_status(db: AsyncSession, patient_id: int, tenant_id: int):
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.ToothStatus).join(models.Patient).where(
            models.ToothStatus.patient_id == patient_id,
            models.ToothStatus.tenant_id == tenant_id,
            models.Patient.tenant_id == tenant_id,
        )
    )
    return result.scalars().all()


async def update_tooth_status(db: AsyncSession, status: schemas.ToothStatusCreate, tenant_id: int):
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.ToothStatus).join(models.Patient).where(
            models.ToothStatus.patient_id == status.patient_id,
            models.ToothStatus.tooth_number == status.tooth_number,
            models.ToothStatus.tenant_id == tenant_id,
            models.Patient.tenant_id == tenant_id,
        )
    )
    db_status = result.scalars().first()
    if db_status:
        db_status.condition = status.condition
        db_status.notes = status.notes
    else:
        db_status = models.ToothStatus(**status.dict(), tenant_id=tenant_id)
        db.add(db_status)
    await db.commit()
    await db.refresh(db_status)
    return db_status


async def create_attachment(
    db: AsyncSession, attachment: schemas.AttachmentCreate, tenant_id: int
):
    _validate_tenant(tenant_id)
    db_attachment = models.Attachment(**attachment.dict(), tenant_id=tenant_id)
    db.add(db_attachment)
    await db.commit()
    await db.refresh(db_attachment)
    return db_attachment


async def get_attachment(db: AsyncSession, attachment_id: int, tenant_id: int):
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.Attachment).join(models.Patient).where(
            models.Attachment.id == attachment_id,
            models.Attachment.tenant_id == tenant_id,
            models.Patient.tenant_id == tenant_id,
            models.Patient.is_deleted == False,
        )
    )
    return result.scalars().first()


async def get_patient_attachments(db: AsyncSession, patient_id: int, tenant_id: int):
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.Attachment).join(models.Patient).where(
            models.Attachment.patient_id == patient_id,
            models.Attachment.tenant_id == tenant_id,
            models.Patient.tenant_id == tenant_id,
        )
    )
    return result.scalars().all()


async def delete_attachment(db: AsyncSession, attachment_id: int, tenant_id: int):
    attachment = await get_attachment(db, attachment_id, tenant_id)
    if attachment:
        await db.delete(attachment)
        await db.commit()
    return attachment


async def create_prescription(
    db: AsyncSession, prescription: schemas.PrescriptionCreate, tenant_id: int
):
    _validate_tenant(tenant_id)
    db_prescription = models.Prescription(**prescription.dict(), tenant_id=tenant_id)
    db.add(db_prescription)
    await db.commit()
    await db.refresh(db_prescription)
    return db_prescription


async def get_prescriptions(db: AsyncSession, patient_id: int, tenant_id: int):
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.Prescription).join(models.Patient).where(
            models.Prescription.patient_id == patient_id,
            models.Prescription.tenant_id == tenant_id,
            models.Patient.tenant_id == tenant_id,
        ).order_by(models.Prescription.date.desc())
    )
    return result.scalars().all()


async def delete_prescription(db: AsyncSession, prescription_id: int, tenant_id: int):
    _validate_tenant(tenant_id)
    result = await db.execute(
        select(models.Prescription).join(models.Patient).where(
            models.Prescription.id == prescription_id,
            models.Prescription.tenant_id == tenant_id,
            models.Patient.tenant_id == tenant_id,
        )
    )
    db_prescription = result.scalars().first()
    if db_prescription:
        await db.delete(db_prescription)
        await db.commit()
    return db_prescription
