from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend import schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.routers.auth import get_async_db
from backend.services.clinical_attachment_link_service import ClinicalAttachmentLinkService

router = APIRouter(
    prefix="/patients/{patient_id}/clinical-attachment-links",
    tags=["Clinical Attachment Links"],
)


@router.post(
    "",
    response_model=StandardResponse[schemas.ClinicalAttachmentLinkRead],
    summary="Create Clinical Attachment Context Link (Slice S23 / G15-M02)",
)
async def create_clinical_attachment_link(
    patient_id: int,
    data: schemas.ClinicalAttachmentLinkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """
    Associate an existing patient attachment with clinical contexts (tooth, work item, care session, event).
    Preserves original attachment record and binary file untouched (G15-M01).
    Fails closed (404) when clinical_vnext_native_writes is disabled.
    """
    service = ClinicalAttachmentLinkService(db, current_user.tenant_id, current_user)
    link = await service.create_attachment_link(patient_id, data)
    return success_response(data=link, message="Clinical attachment link created")


@router.get(
    "",
    response_model=StandardResponse[List[schemas.ClinicalAttachmentLinkRead]],
    summary="List Clinical Attachment Links for Patient",
)
async def list_clinical_attachment_links(
    patient_id: int,
    attachment_id: Optional[int] = Query(None, description="Filter by underlying attachment ID"),
    work_item_id: Optional[int] = Query(None, description="Filter by clinical work item ID"),
    care_session_id: Optional[int] = Query(None, description="Filter by care session ID"),
    clinical_event_id: Optional[int] = Query(None, description="Filter by clinical event ID"),
    tooth_key: Optional[str] = Query(None, description="Filter by FDI tooth notation (11-48, 51-85)"),
    purpose_code: Optional[str] = Query(None, description="Filter by canonical purpose code"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """List clinical attachment links for a patient, optionally filtered by context."""
    service = ClinicalAttachmentLinkService(db, current_user.tenant_id, current_user)
    filters = schemas.ClinicalAttachmentLinkFilter(
        attachment_id=attachment_id,
        work_item_id=work_item_id,
        care_session_id=care_session_id,
        clinical_event_id=clinical_event_id,
        tooth_key=tooth_key,
        purpose_code=purpose_code,
    )
    links = await service.list_attachment_links(patient_id, filters)
    return success_response(data=links, message="Clinical attachment links retrieved")


@router.get(
    "/{link_id}",
    response_model=StandardResponse[schemas.ClinicalAttachmentLinkRead],
    summary="Get Single Clinical Attachment Link",
)
async def get_clinical_attachment_link(
    patient_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Retrieve a single attachment link by ID with tenant and patient boundary verification."""
    service = ClinicalAttachmentLinkService(db, current_user.tenant_id, current_user)
    link = await service.get_attachment_link(patient_id, link_id)
    return success_response(data=link, message="Clinical attachment link retrieved")


@router.delete(
    "/{link_id}",
    response_model=StandardResponse[dict],
    summary="Delete Clinical Attachment Link (Unlink)",
)
async def delete_clinical_attachment_link(
    patient_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    """
    Remove clinical context link.
    CRITICAL: Does NOT delete or alter the underlying Attachment record or file (G15-M01).
    """
    service = ClinicalAttachmentLinkService(db, current_user.tenant_id, current_user)
    res = await service.delete_attachment_link(patient_id, link_id)
    return success_response(data=res, message="Clinical attachment link deleted")
