from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.routers import expenses


class Scalars:
    def first(self):
        return None


class Result:
    def scalars(self):
        return Scalars()


class FakeDb:
    async def execute(self, stmt):
        return Result()


@pytest.mark.asyncio
async def test_delete_missing_expense_returns_404_before_audit(monkeypatch):
    audit_called = False

    def fake_audit(**kwargs):
        nonlocal audit_called
        audit_called = True

    monkeypatch.setattr(expenses, "log_admin_action", fake_audit)
    user = SimpleNamespace(id=2, tenant_id=8, role="admin")

    with pytest.raises(HTTPException) as exc:
        await expenses.delete_expense(404, db=FakeDb(), current_user=user)

    assert exc.value.status_code == 404
    assert audit_called is False
