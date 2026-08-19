from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.core.tenant_context import require_tenant_id


def test_financial_cost_analysis_rejects_missing_tenant_context():
    user = SimpleNamespace(tenant_id=None)

    with pytest.raises(HTTPException) as exc:
        require_tenant_id(user)

    assert exc.value.status_code == 400
    assert "Tenant context" in exc.value.detail


def test_financial_cost_analysis_preserves_real_tenant_id():
    user = SimpleNamespace(tenant_id=27)
    assert require_tenant_id(user) == 27
