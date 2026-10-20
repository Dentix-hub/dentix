from typing import Any, List, Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend import models, schemas
from backend.clinical.catalog import CANONICAL_ATTACHMENT_PURPOSE_CODES
from backend.models.clinical_core import FDI_TOOTH_KEYS
from backend.services.feature_service import FeatureFlagService
from backend.services.patient_access_service import ensure_patient_visible

FEATURE_FLAG_CLINICAL_NATIVE_WRITES = "clinical_vnext_native_writes"


def link_to_read(link: models.ClinicalAttachmentLink) -> schemas.ClinicalAttachmentLinkRead:
    """Helper to convert ClinicalAttachmentLink ORM model to ClinicalAttachmentLinkRead DTO."""
    att = getattr(link, "attachment", None)
    return schemas.ClinicalAttachmentLinkRead(
        id=link.id,
        tenant_id=link.tenant_id,
        patient_id=link.patient_id,
        attachment_id=link.attachment_id,
        work_item_id=link.work_item_id,
        care_session_id=link.care_session_id,
        clinical_event_id=link.clinical_event_id,
        tooth_key=link.tooth_key,
        purpose_code=link.purpose_code,
        notes=link.notes,
        created_at=link.created_at,
        filename=getattr(att, "filename", None) if att else None,
        file_path=getattr(att, "file_path", None) if att else None,
        file_type=getattr(att, "file_type", None) if att else None,
    )


class ClinicalAttachmentLinkService:
    """
    Service managing contextual links between file attachments and clinical entities
    (Tooth, Work Item, Care Session, Clinical Event) per G15-M01, G15-M02, G15-M06.

    Hard Invariants:
    1. Attachment storage and binary files remain 100% untouched (G15-M01).
    2. Only creates, queries, and deletes ClinicalAttachmentLink records (G15-M02).
    3. Purpose codes must belong to canonical allowlist (PD05 / G15-M06).
    4. Strict tenant and patient isolation: referenced attachments, work items,
       sessions, and events MUST belong to the active tenant and patient (RLS / triggers).
    5. Standalone mutations fail-closed when clinical_vnext_native_writes is OFF (404).
    """

    def __init__(self, db: AsyncSession, tenant_id: int, current_user: Any):
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user
        self.current_user_id = getattr(current_user, "id", None)

    async def _get_active_current_user(self) -> Any:
        """Reload user object safely if session was rolled back (R04)."""
        if self.current_user_id is not None:
            stmt = select(models.User).where(
                models.User.id == self.current_user_id,
                models.User.tenant_id == self.tenant_id,
            )
            reloaded = (await self.db.execute(stmt)).scalar_one_or_none()
            if reloaded:
                self.current_user = reloaded
        return self.current_user

    async def is_native_writes_enabled(self) -> bool:
        """Check if native writes feature flag is enabled for this tenant."""
        return await FeatureFlagService.is_feature_enabled(
            self.db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, self.tenant_id
        )

    async def ensure_native_writes_enabled(self) -> None:
        """Fail-closed gate when clinical_vnext_native_writes is OFF (404)."""
        if not await self.is_native_writes_enabled():
            raise HTTPException(
                status_code=404,
                detail="Clinical native writes are disabled",
            )

    async def _verify_patient(self, patient_id: int) -> models.Patient:
        """Validate patient exists, belongs to tenant, and is visible to user."""
        user = await self._get_active_current_user()
        await ensure_patient_visible(self.db, user, patient_id)

        stmt = select(models.Patient).where(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == self.tenant_id,
            models.Patient.is_deleted.is_(False),
        )
        patient = (await self.db.execute(stmt)).scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient

    async def _verify_attachment(self, patient_id: int, attachment_id: int) -> models.Attachment:
        """Validate attachment exists and belongs to the same tenant and patient."""
        stmt = select(models.Attachment).where(
            models.Attachment.id == attachment_id,
            models.Attachment.tenant_id == self.tenant_id,
            models.Attachment.patient_id == patient_id,
        )
        att = (await self.db.execute(stmt)).scalar_one_or_none()
        if not att:
            raise HTTPException(
                status_code=404,
                detail="Attachment not found or does not belong to patient",
            )
        return att

    async def _verify_work_item(self, patient_id: int, work_item_id: int) -> models.ClinicalWorkItem:
        """Validate clinical work item exists and belongs to the same tenant and patient."""
        stmt = select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.id == work_item_id,
            models.ClinicalWorkItem.tenant_id == self.tenant_id,
            models.ClinicalWorkItem.patient_id == patient_id,
        )
        item = (await self.db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=404,
                detail="Clinical work item not found or does not belong to patient",
            )
        return item

    async def _verify_care_session(self, patient_id: int, care_session_id: int) -> models.CareSession:
        """Validate care session exists and belongs to the same tenant and patient."""
        stmt = select(models.CareSession).where(
            models.CareSession.id == care_session_id,
            models.CareSession.tenant_id == self.tenant_id,
            models.CareSession.patient_id == patient_id,
        )
        session = (await self.db.execute(stmt)).scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Care session not found or does not belong to patient",
            )
        return session

    async def _verify_clinical_event(self, patient_id: int, clinical_event_id: int) -> models.ClinicalEvent:
        """Validate clinical event exists and belongs to the same tenant and patient."""
        stmt = select(models.ClinicalEvent).where(
            models.ClinicalEvent.id == clinical_event_id,
            models.ClinicalEvent.tenant_id == self.tenant_id,
            models.ClinicalEvent.patient_id == patient_id,
        )
        ev = (await self.db.execute(stmt)).scalar_one_or_none()
        if not ev:
            raise HTTPException(
                status_code=404,
                detail="Clinical event not found or does not belong to patient",
            )
        return ev

    async def create_attachment_link(
        self, patient_id: int, data: schemas.ClinicalAttachmentLinkCreate
    ) -> schemas.ClinicalAttachmentLinkRead:
        """
        Create a new contextual link associating an existing attachment with clinical contexts (G15-M02).
        Enforces PD05 purpose codes (G15-M06) and strict tenant/patient boundaries.
        Original attachment storage is untouched (G15-M01).
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)
        attachment = await self._verify_attachment(patient_id, data.attachment_id)

        if data.work_item_id is not None:
            await self._verify_work_item(patient_id, data.work_item_id)
        if data.care_session_id is not None:
            await self._verify_care_session(patient_id, data.care_session_id)
        if data.clinical_event_id is not None:
            await self._verify_clinical_event(patient_id, data.clinical_event_id)

        if data.tooth_key is not None and data.tooth_key not in FDI_TOOTH_KEYS:
            raise HTTPException(
                status_code=422,
                detail=f"Tooth key '{data.tooth_key}' is not a valid FDI notation",
            )

        if data.purpose_code not in CANONICAL_ATTACHMENT_PURPOSE_CODES:
            raise HTTPException(
                status_code=422,
                detail=f"Purpose code '{data.purpose_code}' is invalid per PD05 allowlist",
            )

        # Check duplicate exact context link (matching uq_cal_attachment_context_exact)
        dup_stmt = select(models.ClinicalAttachmentLink).where(
            models.ClinicalAttachmentLink.tenant_id == self.tenant_id,
            models.ClinicalAttachmentLink.patient_id == patient_id,
            models.ClinicalAttachmentLink.attachment_id == data.attachment_id,
            models.ClinicalAttachmentLink.work_item_id == data.work_item_id if data.work_item_id is not None else models.ClinicalAttachmentLink.work_item_id.is_(None),
            models.ClinicalAttachmentLink.care_session_id == data.care_session_id if data.care_session_id is not None else models.ClinicalAttachmentLink.care_session_id.is_(None),
            models.ClinicalAttachmentLink.clinical_event_id == data.clinical_event_id if data.clinical_event_id is not None else models.ClinicalAttachmentLink.clinical_event_id.is_(None),
            models.ClinicalAttachmentLink.tooth_key == data.tooth_key if data.tooth_key is not None else models.ClinicalAttachmentLink.tooth_key.is_(None),
        )
        existing = (await self.db.execute(dup_stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Attachment link already exists for this exact clinical context",
            )

        link = models.ClinicalAttachmentLink(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            attachment_id=data.attachment_id,
            work_item_id=data.work_item_id,
            care_session_id=data.care_session_id,
            clinical_event_id=data.clinical_event_id,
            tooth_key=data.tooth_key,
            purpose_code=data.purpose_code,
            notes=data.notes,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)

        # Attach pre-verified attachment object for response serialization
        link.attachment = attachment
        return link_to_read(link)

    async def get_attachment_link(
        self, patient_id: int, link_id: int
    ) -> schemas.ClinicalAttachmentLinkRead:
        """Retrieve a single attachment link by ID with tenant and patient verification."""
        await self._verify_patient(patient_id)
        stmt = (
            select(models.ClinicalAttachmentLink)
            .options(selectinload(models.ClinicalAttachmentLink.attachment))
            .where(
                models.ClinicalAttachmentLink.id == link_id,
                models.ClinicalAttachmentLink.tenant_id == self.tenant_id,
                models.ClinicalAttachmentLink.patient_id == patient_id,
            )
        )
        link = (await self.db.execute(stmt)).scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Clinical attachment link not found")
        return link_to_read(link)

    async def list_attachment_links(
        self,
        patient_id: int,
        filters: Optional[schemas.ClinicalAttachmentLinkFilter] = None,
    ) -> List[schemas.ClinicalAttachmentLinkRead]:
        """List attachment links for a patient, optionally filtered by context."""
        await self._verify_patient(patient_id)
        stmt = (
            select(models.ClinicalAttachmentLink)
            .options(selectinload(models.ClinicalAttachmentLink.attachment))
            .where(
                models.ClinicalAttachmentLink.tenant_id == self.tenant_id,
                models.ClinicalAttachmentLink.patient_id == patient_id,
            )
        )

        if filters:
            if filters.attachment_id is not None:
                stmt = stmt.where(models.ClinicalAttachmentLink.attachment_id == filters.attachment_id)
            if filters.work_item_id is not None:
                stmt = stmt.where(models.ClinicalAttachmentLink.work_item_id == filters.work_item_id)
            if filters.care_session_id is not None:
                stmt = stmt.where(models.ClinicalAttachmentLink.care_session_id == filters.care_session_id)
            if filters.clinical_event_id is not None:
                stmt = stmt.where(models.ClinicalAttachmentLink.clinical_event_id == filters.clinical_event_id)
            if filters.tooth_key is not None:
                stmt = stmt.where(models.ClinicalAttachmentLink.tooth_key == filters.tooth_key)
            if filters.purpose_code is not None:
                stmt = stmt.where(models.ClinicalAttachmentLink.purpose_code == filters.purpose_code)

        stmt = stmt.order_by(
            models.ClinicalAttachmentLink.created_at.desc(),
            models.ClinicalAttachmentLink.id.desc(),
        )
        result = await self.db.execute(stmt)
        links = result.scalars().all()
        return [link_to_read(item) for item in links]

    async def delete_attachment_link(self, patient_id: int, link_id: int) -> dict:
        """
        Delete a clinical context link.
        CRITICAL: Never deletes the underlying Attachment or physical file (G15-M01).
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = select(models.ClinicalAttachmentLink).where(
            models.ClinicalAttachmentLink.id == link_id,
            models.ClinicalAttachmentLink.tenant_id == self.tenant_id,
            models.ClinicalAttachmentLink.patient_id == patient_id,
        )
        link = (await self.db.execute(stmt)).scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Clinical attachment link not found")

        await self.db.delete(link)
        await self.db.commit()
        return {"id": link_id, "deleted": True}
