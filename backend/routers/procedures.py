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
from backend.core.tenant_context import require_tenant_id

router = APIRouter(prefix="/procedures", tags=["Procedures"])


@cache_response(ttl_seconds=300)
async def _get_cached_procedures(db: AsyncSession, tenant_id: int, skip: int, limit: int):
    return await crud.get_procedures(db, tenant_id, skip=skip, limit=limit)


@router.get("")
async def get_procedures(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get tenant procedures plus read-only global templates."""
    tenant_id = require_tenant_id(current_user)
    return await _get_cached_procedures(db, tenant_id, skip, limit)


@router.post("")
async def create_procedure(
    procedure: schemas.ProcedureCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Create a tenant-owned procedure template."""
    tenant_id = require_tenant_id(current_user)
    try:
        result = await crud.create_procedure(
            db=db, procedure=procedure, tenant_id=tenant_id
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    invalidate_cache("_get_cached_procedures")
    return success_response(result)


@router.put("/{procedure_id}")
async def update_procedure(
    procedure_id: int,
    procedure: schemas.ProcedureCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update a tenant-owned procedure template."""
    tenant_id = require_tenant_id(current_user)
    result = await crud.update_procedure(db, procedure_id, procedure, tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Procedure not found")
    invalidate_cache("_get_cached_procedures")
    return success_response(result)


@router.delete("/{procedure_id}")
async def delete_procedure(
    procedure_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a tenant-owned procedure template."""
    tenant_id = require_tenant_id(current_user)
    result = await crud.delete_procedure(db, procedure_id, tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Procedure not found")
    invalidate_cache("_get_cached_procedures")
    return success_response(result)
