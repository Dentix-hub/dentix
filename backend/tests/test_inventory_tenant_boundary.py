from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend.core.tenant_context import require_tenant_id
from backend.routers import inventory as inventory_router
from backend.routers import inventory_smart as inventory_smart_router


def _result(first=None):
    result = MagicMock()
    result.scalars.return_value.first.return_value = first
    return result


def test_require_tenant_id_rejects_platform_context_without_clinic():
    with pytest.raises(HTTPException) as exc:
        require_tenant_id(SimpleNamespace(tenant_id=None))

    assert exc.value.status_code == 400
    assert "Tenant context" in exc.value.detail


def test_require_tenant_id_preserves_real_tenant():
    assert require_tenant_id(SimpleNamespace(tenant_id=42)) == 42


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("guard", "entity_id", "tenant_column"),
    [
        (inventory_router._require_material, 9, "materials.tenant_id"),
        (inventory_router._require_warehouse, 10, "warehouses.tenant_id"),
        (inventory_router._require_stock_item, 11, "stock_items.tenant_id"),
    ],
)
async def test_inventory_id_guards_scope_queries_to_tenant(guard, entity_id, tenant_column):
    db = AsyncMock()
    db.execute.return_value = _result(None)

    with pytest.raises(HTTPException) as exc:
        await guard(db, entity_id, 77)

    assert exc.value.status_code == 404
    statement = db.execute.await_args.args[0]
    rendered = str(statement)
    assert tenant_column in rendered
    assert "tenant_id" in rendered


@pytest.mark.asyncio
async def test_close_session_cannot_resolve_session_outside_current_tenant():
    db = AsyncMock()
    db.execute.return_value = _result(None)
    user = SimpleNamespace(id=3, tenant_id=77)

    with pytest.raises(HTTPException) as exc:
        await inventory_router.close_material_session(
            session_id=123,
            data=SimpleNamespace(total_consumed=None),
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 404
    statement = db.execute.await_args.args[0]
    rendered = str(statement)
    assert "stock_items.tenant_id" in rendered


@pytest.mark.asyncio
async def test_delete_weight_cannot_target_another_tenant_weight():
    db = AsyncMock()
    db.execute.return_value = _result(None)
    user = SimpleNamespace(id=3, tenant_id=77)

    with pytest.raises(HTTPException) as exc:
        await inventory_router.delete_procedure_weight(
            weight_id=321,
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 404
    statement = db.execute.await_args.args[0]
    rendered = str(statement)
    assert "procedure_material_weights.tenant_id" in rendered


@pytest.mark.asyncio
async def test_smart_availability_does_not_resolve_material_from_another_tenant():
    db = AsyncMock()
    db.execute.return_value = _result(None)
    user = SimpleNamespace(id=3, role="admin", tenant_id=77)

    response = await inventory_smart_router.check_availability(
        request_data={"materials": [{"material_id": 999, "quantity": 1}]},
        db=db,
        current_user=user,
    )

    assert response["data"][0]["status"] == "CRITICAL"
    assert response["data"][0]["message"] == "Material not found"
    assert db.execute.await_count == 1
    rendered = str(db.execute.await_args.args[0])
    assert "materials.tenant_id" in rendered


@pytest.mark.asyncio
async def test_smart_suggestions_reject_missing_tenant_context_before_service_call():
    db = AsyncMock()
    user = SimpleNamespace(id=1, role="super_admin", tenant_id=None)

    with pytest.raises(HTTPException) as exc:
        await inventory_smart_router.get_material_suggestions(
            procedure_id=10,
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 400
    db.execute.assert_not_awaited()
