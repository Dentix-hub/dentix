"""Request-time period resolution shared by HTTP, AI, diagnostics and workers."""

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.services.subscription_state_machine import (
    SubscriptionState,
    normalize_state,
)


def utc_naive(value: datetime) -> datetime:
    return (
        value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    )


@dataclass(frozen=True)
class EffectivePeriod:
    status: str
    future_started: bool
    is_past_end: bool
    is_in_grace: bool


def resolve_subscription_period(tenant, now: datetime | None = None) -> EffectivePeriod:
    now = utc_naive(now or datetime.now(timezone.utc))
    raw = getattr(tenant, "subscription_status", "trial")
    status = normalize_state(raw if isinstance(raw, str) else "trial")
    end = getattr(tenant, "subscription_end_date", None)
    grace = getattr(tenant, "grace_period_until", None)
    start = getattr(tenant, "future_plan_start_date", None)
    future_id = getattr(tenant, "future_plan_id", None)
    future_started = bool(
        isinstance(future_id, int)
        and isinstance(start, datetime)
        and now >= utc_naive(start)
    )
    expired = bool(isinstance(end, datetime) and now >= utc_naive(end))
    # A trial with an explicit future paid assignment becomes paid at its start.
    paid = status != SubscriptionState.TRIAL.value or future_started
    in_grace = bool(
        paid and expired and isinstance(grace, datetime) and now < utc_naive(grace)
    )
    if status in {
        SubscriptionState.ACTIVE.value,
        SubscriptionState.TRIAL.value,
        SubscriptionState.GRACE.value,
    }:
        if expired:
            status = (
                SubscriptionState.GRACE.value
                if in_grace
                else SubscriptionState.EXPIRED_READ_ONLY.value
            )
        elif future_started:
            status = SubscriptionState.ACTIVE.value
        elif status == SubscriptionState.GRACE.value:
            status = SubscriptionState.EXPIRED_READ_ONLY.value
    return EffectivePeriod(status, future_started, expired, in_grace)
