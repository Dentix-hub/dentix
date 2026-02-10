from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import schemas, crud
from .auth import get_current_user, get_db

router = APIRouter(prefix="/attachments", tags=["Attachments"])


@router.delete("/{attachment_id}", response_model=schemas.Attachment)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Delete an attachment.
    """
    return crud.delete_attachment(db, attachment_id, current_user.tenant_id)
