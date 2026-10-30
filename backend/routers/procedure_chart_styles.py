"""
Router for procedure chart appearance styles.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud, schemas
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.core.tenant_context import require_tenant_id
from backend.core.response import success_response

router = APIRouter(prefix="/procedure-chart-styles", tags=["Procedure Chart Styles"])


@router.get("", response_model=list[schemas.ProcedureChartStyleRead])
async def get_procedure_chart_styles(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get all procedure chart styles for the current tenant."""
    tenant_id = require_tenant_id(current_user)
    styles = await crud.get_procedure_chart_styles(db, tenant_id)
    return list(styles)


@router.put("", response_model=schemas.ProcedureChartStyleRead)
async def upsert_procedure_chart_style(
    style_in: schemas.ProcedureChartStyleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Create or update a procedure chart style for the current tenant."""
    tenant_id = require_tenant_id(current_user)

    # Validate procedure exists in tenant or global catalog (exact match)
    exists = await crud.procedure_exists_for_tenant(
        db, tenant_id=tenant_id, procedure_name=style_in.procedure_name
    )
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Procedure '{style_in.procedure_name}' does not exist in the tenant or global catalog.",
        )

    style = await crud.upsert_procedure_chart_style(
        db, tenant_id=tenant_id, style_in=style_in
    )
    return style


@router.delete("/{style_id}")
async def delete_procedure_chart_style(
    style_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a procedure chart style for the current tenant."""
    tenant_id = require_tenant_id(current_user)
    deleted = await crud.delete_procedure_chart_style(
        db, style_id=style_id, tenant_id=tenant_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedure chart style not found.",
        )
    return success_response({"message": "Procedure chart style deleted successfully."})
