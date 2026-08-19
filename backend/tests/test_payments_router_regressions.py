from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.routers import payments


class FakeDb:
    def __init__(self):
        self.rolled_back = False

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_delete_payment_missing_returns_404_and_rolls_back_audit(monkeypatch):
    db = FakeDb()
    user = SimpleNamespace(id=7, tenant_id=4, role="admin")

    monkeypatch.setattr(payments, "log_admin_action", lambda **kwargs: None)

    async def fake_delete_payment(db_arg, payment_id, tenant_id):
        assert db_arg is db
        assert payment_id == 99
        assert tenant_id == 4
        return None

    monkeypatch.setattr(payments.crud, "delete_payment", fake_delete_payment)

    with pytest.raises(HTTPException) as exc:
        await payments.delete_payment(99, db=db, current_user=user)

    assert exc.value.status_code == 404
    assert db.rolled_back is True
