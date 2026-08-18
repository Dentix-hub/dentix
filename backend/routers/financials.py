from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.database import get_async_db
from backend import schemas
from backend.services.cost_engine import CostEngine
from backend.core.permissions import Permission, require_permission
from backend.core.tenant_context import require_tenant_id

router = APIRouter(prefix="/financials", tags=["Financials"])
logger = logging.getLogger("smart_clinic")


@router.get("/procedure/{procedure_id}/analysis")
async def analyze_procedure_cost(
    procedure_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get detailed cost breakdown for a procedure based on BOM."""
    tenant_id = require_tenant_id(current_user)
    engine = CostEngine(db, tenant_id)
    try:
        return await engine.calculate_procedure_cost(procedure_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Procedure cost analysis error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate procedure cost") from e


@router.get("/procedures/analysis")
async def analyze_all_procedures_cost(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get high-level cost analysis for all tenant-visible procedures."""
    tenant_id = require_tenant_id(current_user)
    engine = CostEngine(db, tenant_id)
    try:
        return await engine.calculate_all_procedures_costs()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Bulk analysis error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate bulk analysis") from e
