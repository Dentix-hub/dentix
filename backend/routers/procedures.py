"""
Procedures Router
Handles dental procedure templates.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.core.response import success_response
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas, crud
from ..cache import cache_response, invalidate_cache
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission

router = APIRouter(prefix="/procedures", tags=["Procedures"])


# Helper function to cache procedures per tenant
@cache_response(ttl_seconds=300)  # Cache for 5 minutes
async def _get_cached_procedures(db: AsyncSession, tenant_id: int, skip: int, limit: int):
    return await crud.get_procedures(db, tenant_id, skip=skip, limit=limit)


@router.get("")
async def get_procedures(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get all procedure templates for current tenant. (Cached for 5 min)"""
    return await _get_cached_procedures(db, current_user.tenant_id or 1, skip, limit)


@router.post("")
async def create_procedure(
    procedure: schemas.ProcedureCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Create a new procedure template."""
    try:
        result = await crud.create_procedure(
            db=db, procedure=procedure, tenant_id=current_user.tenant_id
        )
    except ValueError as e:
        # CRUD raises ValueError on duplicate name (IntegrityError on ix_procedures_name)
        # after rolling back, so the session is clean. Surface as a 409 Conflict.
        raise HTTPException(status_code=409, detail=str(e))
    # Invalidate cache for this function
    invalidate_cache("_get_cached_procedures")
    return success_response(result)


@router.put("/{procedure_id}")
async def update_procedure(
    procedure_id: int,
    procedure: schemas.ProcedureCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update a procedure template."""
    result = await crud.update_procedure(db, procedure_id, procedure, current_user.tenant_id)
    invalidate_cache("_get_cached_procedures")
    return success_response(result)


@router.delete("/{procedure_id}")
async def delete_procedure(
    procedure_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a procedure template."""
    result = await crud.delete_procedure(db, procedure_id, current_user.tenant_id)
    invalidate_cache("_get_cached_procedures")
    return success_response(result)
