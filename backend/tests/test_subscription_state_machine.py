"""
Table-driven tests for backend/services/subscription_state_machine.py
"""

import pytest
from backend.services.subscription_state_machine import (
    validate_transition,
    normalize_state,
    SubscriptionState,
    InvalidSubscriptionTransitionError,
)


@pytest.mark.parametrize(
    "from_state, to_state, expected",
    [
        ("trial", "active", "active"),
        ("trial", "grace", "grace"),
        ("trial", "expired_read_only", "expired_read_only"),
        ("trial", "expired", "expired_read_only"),
        ("active", "grace", "grace"),
        ("active", "expired_read_only", "expired_read_only"),
        ("active", "suspended_admin", "suspended_admin"),
        ("grace", "active", "active"),
        ("expired_read_only", "active", "active"),
        ("expired", "active", "active"),
        ("suspended_admin", "active", "active"),
        ("cancelled", "active", "active"),
        ("active", "active", "active"),
    ],
)
def test_allowed_transitions(from_state, to_state, expected):
    result = validate_transition(from_state, to_state)
    assert result == expected


@pytest.mark.parametrize(
    "from_state, to_state",
    [
        ("suspended_admin", "trial"),
        ("suspended_admin", "grace"),
        ("suspended_admin", "expired_read_only"),
        ("cancelled", "grace"),
        ("cancelled", "trial"),
        ("expired_read_only", "trial"),
        ("active", "trial"),
    ],
)
def test_forbidden_transitions(from_state, to_state):
    with pytest.raises(InvalidSubscriptionTransitionError, match="Forbidden subscription transition"):
        validate_transition(from_state, to_state)


def test_invalid_state_name_raises():
    with pytest.raises(InvalidSubscriptionTransitionError, match="Unknown subscription state"):
        normalize_state("super_vip_lifetime")
