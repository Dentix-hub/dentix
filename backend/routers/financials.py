from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.routers.auth import get_current_user
from backend import schemas
from backend.services.cost_engine import CostEngine

router = APIRouter(prefix="/financials", tags=["Financials"])

@router.get("/procedure/{procedure_id}/analysis")
def analyze_procedure_cost(
    procedure_id: int, 
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    """
    Get detailed cost breakdown for a procedure based on BOM.
    """
    if current_user.role not in ["super_admin", "admin", "manager", "doctor"]:
        raise HTTPException(status_code=403, detail="Not authorized to view financial data")

    engine = CostEngine(db, current_user.tenant_id or 1)
    try:
        return engine.calculate_procedure_cost(procedure_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/procedures/analysis")
def analyze_all_procedures_cost(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    """
    Get high-level cost analysis for ALL procedures.
    Used for General Analysis dashboard.
    """
    if current_user.role not in ["super_admin", "admin", "manager", "doctor"]:
        raise HTTPException(status_code=403, detail="Not authorized to view financial data")

    engine = CostEngine(db, current_user.tenant_id or 1)
    try:
        return engine.calculate_all_procedures_costs()
    except Exception as e:
        print(f"Error in bulk analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate bulk analysis")
