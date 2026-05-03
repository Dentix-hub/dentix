from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from backend.database import get_db
from backend import schemas
from backend.services.cost_engine import CostEngine
from backend.core.permissions import Permission, require_permission

router = APIRouter(prefix="/financials", tags=["Financials"])
logger = logging.getLogger("smart_clinic")


@router.get("/procedure/{procedure_id}/analysis")
def analyze_procedure_cost(
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """
    Get detailed cost breakdown for a procedure based on BOM.
    """

    engine = CostEngine(db, current_user.tenant_id or 1)
    try:
        return engine.calculate_procedure_cost(procedure_id)
    except Exception as e:
        logger.error(f"Procedure cost analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/procedures/analysis")
def analyze_all_procedures_cost(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """
    Get high-level cost analysis for ALL procedures.
    Used for General Analysis dashboard.
    """

    engine = CostEngine(db, current_user.tenant_id or 1)
    try:
        return engine.calculate_all_procedures_costs()
    except Exception as e:
        logger.error(f"Bulk analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate bulk analysis")
