from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.database import get_async_db
from backend.routers.auth import get_current_user
from backend.services.onboarding_service import OnboardingService
from backend.schemas.onboarding import (
    OnboardingStatusResponse,
    OnboardingEventRequest,
    OnboardingDismissRequest,
)

router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"],
)


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns the onboarding checklist status, steps, and seen tooltips for the caller's role.
    If the feature flag is disabled for the tenant, returns enabled: false with no steps.
    """
    return await OnboardingService.get_status(db, current_user)


@router.post("/dismiss")
async def dismiss_onboarding(
    payload: OnboardingDismissRequest = OnboardingDismissRequest(dismissed=True),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Dismiss the onboarding checklist for the current user.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    state = await OnboardingService.set_dismissed(
        db, current_user.tenant_id, current_user.id, payload.dismissed
    )
    return {"status": "success", "dismissed": state.dismissed}


@router.post("/restore")
async def restore_onboarding(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Restore (un-dismiss) the onboarding checklist for the current user.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    state = await OnboardingService.set_dismissed(
        db, current_user.tenant_id, current_user.id, False
    )
    return {"status": "success", "dismissed": state.dismissed}


@router.post("/tips/{tip_key}")
async def record_tip_seen(
    tip_key: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Record that a first-visit tooltip was seen/dismissed by the current user.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    state = await OnboardingService.record_tip_seen(
        db, current_user.tenant_id, current_user.id, tip_key
    )
    return {"status": "success", "seen_tips": state.seen_tips}


@router.post("/events")
async def record_onboarding_event(
    payload: OnboardingEventRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Record a client-triggered onboarding event (e.g. patient_file_opened, daily_report_viewed).
    Only whitelisted event keys are accepted.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")
    state = await OnboardingService.record_event(
        db, current_user.tenant_id, current_user.id, payload.event_key
    )
    return {"status": "success", "event_key": payload.event_key}
