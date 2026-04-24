"""
AI Router - Smart Dent Clinic
Handles AI query endpoint via AIService.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import logging

from backend import models
from backend.routers.auth import get_db
from backend.services.ai_service import AIService
from backend.schemas.ai import AIQueryRequest, AIQueryResponse
from backend.ai.tools.registry import tool_registry
from backend.core.limiter import limiter
from backend.core.permissions import Permission, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/query", response_model=AIQueryResponse)
@limiter.limit("10/minute")
async def ai_query(
    query_data: AIQueryRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.AI_CHAT)),
):
    """
    Process AI queries using the Smart Agent Service.
    """
    service = AIService(db, current_user)
    trace_id = getattr(request.state, "trace_id", None)

    return await service.process_query(
        text=query_data.text,
        context=[m.dict() for m in query_data.context] if query_data.context else None,
        last_patient_name=query_data.last_patient_name,
        trace_id=trace_id,
        scribe_mode=query_data.scribe_mode,
    )


@router.get("/tools")
async def list_tools(
    current_user: models.User = Depends(require_permission(Permission.AI_CHAT)),
):
    """List all available AI tools."""
    tools = tool_registry.all()
    return {
        "tools": [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in tools
        ]
    }
