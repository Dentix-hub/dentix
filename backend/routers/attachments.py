from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from .auth import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.services.visibility_service import get_visibility_service

router = APIRouter(prefix="/attachments", tags=["Attachments"])


@router.delete("/{attachment_id}", response_model=schemas.Attachment)
async def delete_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_UPDATE)),
):
    attachment = await crud.get_attachment(db, attachment_id, current_user.tenant_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    if not await visibility.can_view_patient(attachment.patient_id):
        raise HTTPException(status_code=404, detail="Attachment not found")
    return await crud.delete_attachment(db, attachment_id, current_user.tenant_id)
