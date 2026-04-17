from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import schemas, crud
from .auth import get_db
from backend.core.permissions import Permission, require_permission

router = APIRouter(prefix="/attachments", tags=["Attachments"])


@router.delete("/{attachment_id}", response_model=schemas.Attachment)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_UPDATE)),
):
    """
    Delete an attachment.
    """
    return crud.delete_attachment(db, attachment_id, current_user.tenant_id)
