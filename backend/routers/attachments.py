from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, crud
from .auth import get_async_db
from backend.core.permissions import Permission, require_permission

router = APIRouter(prefix="/attachments", tags=["Attachments"])


@router.delete("/{attachment_id}", response_model=schemas.Attachment)
async def delete_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_UPDATE)),
):
    """
    Delete an attachment.
    """
    return await crud.delete_attachment(db, attachment_id, current_user.tenant_id)
