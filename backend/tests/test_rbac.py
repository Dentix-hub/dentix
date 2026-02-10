"""
RBAC Tests
Tests for Role-Based Access Control enforcement.
"""

import pytest
from fastapi import HTTPException
from backend import models
from backend.constants import ROLES
from backend.routers.admin import require_super_admin


def test_require_super_admin_allows_super_admin():
    """Super admin should be allowed."""
    user = models.User(role=ROLES.SUPER_ADMIN, username="super", id=1)
    result = require_super_admin(user)
    assert result == user


def test_require_super_admin_denies_doctor():
    """Doctor should be denied access."""
    user = models.User(role=ROLES.DOCTOR, username="doc", id=2)
    with pytest.raises(HTTPException) as exc:
        require_super_admin(user)
    assert exc.value.status_code == 403


def test_require_super_admin_denies_manager():
    """Manager should be denied access."""
    user = models.User(role=ROLES.MANAGER, username="manager", id=3)
    with pytest.raises(HTTPException) as exc:
        require_super_admin(user)
    assert exc.value.status_code == 403


# TODO: Add more specific role dependency tests if they exist in other routers.
# For now, admin router is the main protected area we know has a decorator.
