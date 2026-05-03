from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Any
import logging

from backend import database, models
from backend.schemas import User
from backend.core.tenancy import get_current_tenant_id
from backend.ai.agent.state_manager import state_manager
from backend.core.permissions import Permission, require_permission

router = APIRouter(prefix="/ai", tags=["AI Assist"])
logger = logging.getLogger(__name__)


@router.get("/autocomplete")
def ai_autocomplete(
    q: str = Query(..., min_length=1),
    context: str = Query(None),  # e.g., 'registration', 'search'
    db: Session = Depends(database.get_db),
    current_user: User = Depends(require_permission(Permission.AI_CHAT)),
    tenant_id: int = Depends(get_current_tenant_id),
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fast autocomplete for AI-driven inputs.
    Returns patients and context-aware suggestions.
    """
    results = {"patients": [], "suggestions": []}

    # 1. Patient Fuzzy Search
    if len(q) >= 2:
        # Simple ILIKE for now, can be upgraded to Trigram/Fuzzy
        patients = (
            db.query(models.Patient)
            .filter(
                models.Patient.tenant_id == tenant_id,
                or_(
                    models.Patient.name.ilike(f"%{q}%"),
                    models.Patient.phone.ilike(f"%{q}%"),
                ),
            )
            .limit(5)
            .all()
        )

        for p in patients:
            results["patients"].append(
                {
                    "id": p.id,
                    "name": p.name,
                    "phone": p.phone,
                    "displayText": f"{p.name} ({p.phone})",
                }
            )

    # 2. Contextual Suggestions (Next Actions)
    # Check session state
    session = state_manager.get_session(tenant_id, current_user.id)

    if session.active_patient_id:
        # If we have an active patient, suggest actions for them
        results["suggestions"].append(
            {
                "type": "action",
                "text": f"حجز موعد لـ {session.active_patient_name}",
                "intent": "smart_book_appointment",
                "params": {"patient_name": session.active_patient_name},
            }
        )
        results["suggestions"].append(
            {
                "type": "action",
                "text": f"ماليات {session.active_patient_name}",
                "intent": "get_financial_record",
                "params": {"patient_name": session.active_patient_name},
            }
        )

    return results
