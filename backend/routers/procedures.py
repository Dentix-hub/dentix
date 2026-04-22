"""
Procedures Router
Handles dental procedure templates.
"""

from fastapi import APIRouter, Depends
from backend.core.response import success_response
from sqlalchemy.orm import Session

from .. import schemas, crud
from ..cache import cache_response, invalidate_cache
from .auth import get_db
from backend.core.permissions import Permission, require_permission

router = APIRouter(prefix="/procedures", tags=["Procedures"])


# Helper function to cache procedures per tenant
@cache_response(ttl_seconds=300)  # Cache for 5 minutes
def _get_cached_procedures(db: Session, tenant_id: int, skip: int, limit: int):
    return crud.get_procedures(db, tenant_id, skip=skip, limit=limit)


@router.get("")
def get_procedures(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get all procedure templates for current tenant. (Cached for 5 min)"""
    return _get_cached_procedures(db, current_user.tenant_id or 1, skip, limit)


@router.post("")
def create_procedure(
    procedure: schemas.ProcedureCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Create a new procedure template."""
    result = crud.create_procedure(
        db=db, procedure=procedure, tenant_id=current_user.tenant_id
    )
    # Invalidate cache for this function
    invalidate_cache("_get_cached_procedures")
    return success_response(result)


@router.put("/{procedure_id}")
def update_procedure(
    procedure_id: int,
    procedure: schemas.ProcedureCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update a procedure template."""
    result = crud.update_procedure(db, procedure_id, procedure, current_user.tenant_id)
    invalidate_cache("_get_cached_procedures")
    return success_response(result)


@router.delete("/{procedure_id}")
def delete_procedure(
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a procedure template."""
    result = crud.delete_procedure(db, procedure_id, current_user.tenant_id)
    invalidate_cache("_get_cached_procedures")
    return success_response(result)
