"""Current-user push subscription lifecycle (plan §12.3).

All identity fields are derived from the authenticated request context.
Endpoints require an authenticated session (and the platform CSRF flow that
already guards state-changing API traffic).
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import auth, models, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.services.web_push_service import MAX_ACTIVE_SUBSCRIPTIONS_PER_USER, web_push_service
from backend.database import get_async_db
from .auth.dependencies import get_token_from_header_or_cookie

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/push", tags=["Push"])


def _require_session_sid(token: str | None) -> str:
    """Extract the stable session identity from the authenticated access token.

    The client never sends its sid: subscriptions are bound server-side to the
    session that created them so logout/session replacement can disassociate
    them deterministically (plan §2.11 / §12.2).
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except auth.JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc
    sid = payload.get("sid")
    if not sid or not isinstance(sid, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Push subscriptions require a valid session",
        )
    return sid


@router.post("/subscriptions", response_model=StandardResponse[schemas.PushSubscriptionRead])
async def register_subscription(
    data: schemas.PushSubscriptionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PATIENT_READ)),
    token: str | None = Depends(get_token_from_header_or_cookie),
):
    """Register the current browser installation for push delivery."""
    session_sid = _require_session_sid(token)
    subscription = await web_push_service.register_subscription(db, current_user, session_sid, data)
    return success_response(data=subscription, message="Push subscription registered")


@router.get("/subscriptions/me", response_model=StandardResponse[List[schemas.PushSubscriptionRead]])
async def list_my_subscriptions(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    """List the current user's active push installations."""
    subscriptions = await web_push_service.list_user_subscriptions(db, current_user.id)
    return success_response(data=subscriptions, message="Subscriptions retrieved")


@router.post("/subscriptions/refresh", response_model=StandardResponse[schemas.PushSubscriptionRead])
async def refresh_subscription(
    data: schemas.PushSubscriptionRefresh,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PATIENT_READ)),
    token: str | None = Depends(get_token_from_header_or_cookie),
):
    """Rotate keys of an existing installation (pushsubscriptionchange)."""
    session_sid = _require_session_sid(token)
    subscription = await web_push_service.refresh_subscription(
        db,
        current_user,
        session_sid,
        data.endpoint,
        data.keys.p256dh,
        data.keys.auth,
    )
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return success_response(data=subscription, message="Push subscription refreshed")


@router.delete("/subscriptions/{subscription_id}")
async def revoke_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    """Revoke one of the current user's installations."""
    revoked = await web_push_service.revoke_subscription(db, current_user.id, subscription_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return success_response(data={"revoked": True}, message="Push subscription revoked")


@router.delete("/subscriptions")
async def revoke_all_subscriptions(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    """Revoke every installation (security settings: sign out all devices)."""
    count = await web_push_service.revoke_all_for_user(db, current_user.id)
    return success_response(data={"revoked": count}, message="All push subscriptions revoked")


__all__ = ["router", "MAX_ACTIVE_SUBSCRIPTIONS_PER_USER"]
