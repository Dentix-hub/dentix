"""
DENTIX Subscription State Machine
Centralized subscription states and transition rules.
Keeps account activation (is_active) separate from subscription entitlement states.
"""

from enum import Enum
from typing import Set, Tuple


class SubscriptionState(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED_READ_ONLY = "expired_read_only"
    EXPIRED = "expired"  # Alias for backward compatibility
    SUSPENDED_ADMIN = "suspended_admin"
    CANCELLED = "cancelled"


# Canonical normalized states
CANONICAL_STATES: Set[str] = {
    SubscriptionState.TRIAL.value,
    SubscriptionState.ACTIVE.value,
    SubscriptionState.GRACE.value,
    SubscriptionState.EXPIRED_READ_ONLY.value,
    SubscriptionState.SUSPENDED_ADMIN.value,
    SubscriptionState.CANCELLED.value,
}

# Allowed directed transitions (from_state, to_state)
ALLOWED_TRANSITIONS: Set[Tuple[str, str]] = {
    # From trial
    (SubscriptionState.TRIAL.value, SubscriptionState.ACTIVE.value),
    (SubscriptionState.TRIAL.value, SubscriptionState.GRACE.value),
    (SubscriptionState.TRIAL.value, SubscriptionState.EXPIRED_READ_ONLY.value),
    (SubscriptionState.TRIAL.value, SubscriptionState.CANCELLED.value),
    (SubscriptionState.TRIAL.value, SubscriptionState.SUSPENDED_ADMIN.value),
    # From active
    (SubscriptionState.ACTIVE.value, SubscriptionState.GRACE.value),
    (SubscriptionState.ACTIVE.value, SubscriptionState.EXPIRED_READ_ONLY.value),
    (SubscriptionState.ACTIVE.value, SubscriptionState.CANCELLED.value),
    (SubscriptionState.ACTIVE.value, SubscriptionState.SUSPENDED_ADMIN.value),
    # From grace
    (SubscriptionState.GRACE.value, SubscriptionState.ACTIVE.value),
    (SubscriptionState.GRACE.value, SubscriptionState.EXPIRED_READ_ONLY.value),
    (SubscriptionState.GRACE.value, SubscriptionState.CANCELLED.value),
    (SubscriptionState.GRACE.value, SubscriptionState.SUSPENDED_ADMIN.value),
    # From expired_read_only
    (SubscriptionState.EXPIRED_READ_ONLY.value, SubscriptionState.ACTIVE.value),
    (SubscriptionState.EXPIRED_READ_ONLY.value, SubscriptionState.CANCELLED.value),
    (SubscriptionState.EXPIRED_READ_ONLY.value, SubscriptionState.SUSPENDED_ADMIN.value),
    # From suspended_admin
    (SubscriptionState.SUSPENDED_ADMIN.value, SubscriptionState.ACTIVE.value),
    (SubscriptionState.SUSPENDED_ADMIN.value, SubscriptionState.CANCELLED.value),
    # From cancelled
    (SubscriptionState.CANCELLED.value, SubscriptionState.ACTIVE.value),
}


class InvalidSubscriptionTransitionError(ValueError):
    """Raised when attempting an unauthorized or invalid subscription state transition."""
    pass


def normalize_state(state: str) -> str:
    """Normalize legacy state strings."""
    if not state:
        return SubscriptionState.TRIAL.value
    s = state.lower().strip()
    if s == "expired":
        return SubscriptionState.EXPIRED_READ_ONLY.value
    if s not in CANONICAL_STATES:
        raise InvalidSubscriptionTransitionError(
            f"Unknown subscription state '{state}'. Allowed: {sorted(list(CANONICAL_STATES))}"
        )
    return s


def validate_transition(current_state: str, target_state: str) -> str:
    """
    Validate that transitioning from current_state to target_state is permitted.
    Returns normalized target_state.
    Raises InvalidSubscriptionTransitionError if forbidden.
    """
    curr = normalize_state(current_state)
    target = normalize_state(target_state)

    if curr == target:
        return target

    if (curr, target) not in ALLOWED_TRANSITIONS:
        raise InvalidSubscriptionTransitionError(
            f"Forbidden subscription transition from '{curr}' to '{target}'."
        )

    return target
