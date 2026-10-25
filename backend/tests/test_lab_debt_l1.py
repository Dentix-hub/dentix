"""Tests for Slice L1: Lab debt vs paid data model + order payment status + payments API.

All tests are verified to fail against the staging baseline (pre-L1) and pass post-L1.
"""

import os
import tempfile
from decimal import Decimal
from datetime import datetime, timezone
import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic import command
from fastapi import HTTPException

from backend import models, schemas
from backend.core.money import quantize_money
from backend.routers.laboratories import (
    create_lab_order,
    create_lab_payment,
    delete_lab_order,
    get_lab_order,
    get_lab_orders,
    get_lab_stats,
    get_patient_lab_orders,
    update_lab_order,
)
try:
    from backend.services.lab_service import LabService, get_order_payment_map
except ImportError:
    from backend.services.lab_service import LabService
    get_order_payment_map = None
from backend.services.export_service import export_tenant_data
from backend.services.import_service import import_tenant_data


@pytest.fixture
async def l1_setup(async_db_session, test_user, test_patient):
    """Seed a laboratory for L1 tests."""
    lab = models.Laboratory(
        name="L1 Test Laboratory",
        phone="0123456789",
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    async_db_session.add(lab)
    await async_db_session.flush()
    return {"lab": lab, "patient": test_patient, "user": test_user}


# ---------------------------------------------------------------------------
# 1. Status matrix (all 5 states: no_cost, cancelled, unpaid, partial, paid)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_lab_order_payment_status_matrix(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    # 1. no_cost (cost == 0)
    res_no_cost = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Crown",
            cost=Decimal("0.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    data = res_no_cost["data"]
    assert data["payment_status"] == "no_cost"
    assert Decimal(str(data["paid_amount"])) == Decimal("0.00")
    assert Decimal(str(data["remaining_amount"])) == Decimal("0.00")

    # 2. unpaid (cost > 0, paid == 0)
    res_unpaid = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Bridge",
            cost=Decimal("500.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    data = res_unpaid["data"]
    order_id = data["id"]
    assert data["payment_status"] == "unpaid"
    assert Decimal(str(data["paid_amount"])) == Decimal("0.00")
    assert Decimal(str(data["remaining_amount"])) == Decimal("500.00")

    # 3. partial (0 < paid < cost)
    await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=order_id,
            amount=Decimal("200.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    res_get = await get_lab_order(order_id=order_id, db=async_db_session, current_user=user)
    data = res_get["data"]
    assert data["payment_status"] == "partial"
    assert Decimal(str(data["paid_amount"])) == Decimal("200.00")
    assert Decimal(str(data["remaining_amount"])) == Decimal("300.00")

    # 4. paid (paid >= cost > 0)
    await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=order_id,
            amount=Decimal("300.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    res_get2 = await get_lab_order(order_id=order_id, db=async_db_session, current_user=user)
    data = res_get2["data"]
    assert data["payment_status"] == "paid"
    assert Decimal(str(data["paid_amount"])) == Decimal("500.00")
    assert Decimal(str(data["remaining_amount"])) == Decimal("0.00")

    # 5. cancelled (status == cancelled)
    res_cancelled_order = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Inlay",
            cost=Decimal("300.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    cancelled_id = res_cancelled_order["data"]["id"]
    await update_lab_order(
        order_id=cancelled_id,
        order_update=schemas.LabOrderUpdate(status="cancelled"),
        db=async_db_session,
        current_user=user,
    )
    res_get3 = await get_lab_order(order_id=cancelled_id, db=async_db_session, current_user=user)
    data = res_get3["data"]
    assert data["payment_status"] == "cancelled"
    assert Decimal(str(data["remaining_amount"])) == Decimal("0.00")


# ---------------------------------------------------------------------------
# 2. Partial then full payment
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_partial_then_full_payment(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Zirconia Crown",
            cost=Decimal("400.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    order_id = res["data"]["id"]

    # First partial payment: 150
    pay1 = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            lab_order_id=order_id,
            amount=Decimal("150.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    pay1_data = pay1["data"]
    pay1_order_id = pay1_data["lab_order_id"] if isinstance(pay1_data, dict) else pay1_data.lab_order_id
    assert pay1_order_id == order_id

    order_fetched = (await get_lab_order(order_id=order_id, db=async_db_session, current_user=user))["data"]
    assert order_fetched["payment_status"] == "partial"
    assert Decimal(str(order_fetched["paid_amount"])) == Decimal("150.00")
    assert Decimal(str(order_fetched["remaining_amount"])) == Decimal("250.00")

    # Second full payment: 250
    pay2 = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            lab_order_id=order_id,
            amount=Decimal("250.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    pay2_data = pay2["data"]
    pay2_order_id = pay2_data["lab_order_id"] if isinstance(pay2_data, dict) else pay2_data.lab_order_id
    assert pay2_order_id == order_id

    order_fetched2 = (await get_lab_order(order_id=order_id, db=async_db_session, current_user=user))["data"]
    assert order_fetched2["payment_status"] == "paid"
    assert Decimal(str(order_fetched2["paid_amount"])) == Decimal("400.00")
    assert Decimal(str(order_fetched2["remaining_amount"])) == Decimal("0.00")


# ---------------------------------------------------------------------------
# 3. Overpay rejected with Arabic error
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_overpay_rejected(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Veneer",
            cost=Decimal("200.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    order_id = res["data"]["id"]

    # Attempt to overpay immediately (250 > 200)
    with pytest.raises(HTTPException) as exc:
        await create_lab_payment(
            lab_id=lab.id,
            payment=schemas.LabPaymentCreate(
                lab_order_id=order_id,
                amount=Decimal("250.00"),
            ),
            db=async_db_session,
            current_user=user,
        )
    assert exc.value.status_code == 400
    assert "يتجاوز" in exc.value.detail or "المتبقي" in exc.value.detail

    # Pay 150
    await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            lab_order_id=order_id,
            amount=Decimal("150.00"),
        ),
        db=async_db_session,
        current_user=user,
    )

    # Attempt to pay 60 (remaining is 50)
    with pytest.raises(HTTPException) as exc2:
        await create_lab_payment(
            lab_id=lab.id,
            payment=schemas.LabPaymentCreate(
                lab_order_id=order_id,
                amount=Decimal("60.00"),
            ),
            db=async_db_session,
            current_user=user,
        )
    assert exc2.value.status_code == 400
    assert "يتجاوز" in exc2.value.detail or "المتبقي" in exc2.value.detail


# ---------------------------------------------------------------------------
# 4. Cross-tenant and cross-lab lab_order_id rejected
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cross_tenant_and_cross_lab_payment_rejected(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    # Create second lab in same tenant
    lab2 = models.Laboratory(
        name="Second Lab",
        tenant_id=user.tenant_id,
        is_active=True,
    )
    # Create other tenant + other lab + other order
    other_tenant = models.Tenant(name="Other Tenant", is_active=True)
    async_db_session.add_all([lab2, other_tenant])
    await async_db_session.flush()

    other_patient = models.Patient(
        name="Other Patient",
        age=30,
        medical_history="None",
        notes="",
        tenant_id=other_tenant.id,
        phone="0111111111",
        is_deleted=False,
    )
    other_lab = models.Laboratory(
        name="Other Tenant Lab",
        tenant_id=other_tenant.id,
        is_active=True,
    )
    async_db_session.add_all([other_patient, other_lab])
    await async_db_session.flush()

    other_order = models.LabOrder(
        patient_id=other_patient.id,
        laboratory_id=other_lab.id,
        work_type="Crown",
        cost=Decimal("300.00"),
        tenant_id=other_tenant.id,
    )
    lab1_order = models.LabOrder(
        patient_id=patient.id,
        laboratory_id=lab.id,
        work_type="Crown",
        cost=Decimal("300.00"),
        tenant_id=user.tenant_id,
    )
    async_db_session.add_all([other_order, lab1_order])
    await async_db_session.flush()

    # 1. Cross-tenant order_id must be 404
    with pytest.raises(HTTPException) as exc_tenant:
        await create_lab_payment(
            lab_id=lab.id,
            payment=schemas.LabPaymentCreate(
                lab_order_id=other_order.id,
                amount=Decimal("100.00"),
            ),
            db=async_db_session,
            current_user=user,
        )
    assert exc_tenant.value.status_code == 404

    # 2. Cross-lab order_id must be 400
    with pytest.raises(HTTPException) as exc_lab:
        await create_lab_payment(
            lab_id=lab2.id,  # paying to lab2 with order that belongs to lab1
            payment=schemas.LabPaymentCreate(
                lab_order_id=lab1_order.id,
                amount=Decimal("100.00"),
            ),
            db=async_db_session,
            current_user=user,
        )
    assert exc_lab.value.status_code == 400
    assert "المعمل" in exc_lab.value.detail


# ---------------------------------------------------------------------------
# 5. Cancelled order rejected for payment and excluded from balance
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cancelled_order_rejected_for_payment_and_excluded_from_balance(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Cancelled Work",
            cost=Decimal("350.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    order_id = res["data"]["id"]

    # Cancel the order
    await update_lab_order(
        order_id=order_id,
        order_update=schemas.LabOrderUpdate(status="cancelled"),
        db=async_db_session,
        current_user=user,
    )

    # Attempt to pay against cancelled order -> 400
    with pytest.raises(HTTPException) as exc:
        await create_lab_payment(
            lab_id=lab.id,
            payment=schemas.LabPaymentCreate(
                lab_order_id=order_id,
                amount=Decimal("100.00"),
            ),
            db=async_db_session,
            current_user=user,
        )
    assert exc.value.status_code == 400
    assert "ملغي" in exc.value.detail

    # Lab stats balance must exclude cancelled order
    stats = await get_lab_stats(lab_id=lab.id, db=async_db_session, current_user=user)
    assert stats["total_cost"] == 0.0
    assert stats["balance"] == 0.0
    assert stats["unpaid_orders_count"] == 0


# ---------------------------------------------------------------------------
# 6. paid_now atomicity (payment insert failure rolls back order row)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_lab_order_paid_now_atomicity(async_db_session, l1_setup, monkeypatch):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    # 1. paid_now > cost rejected with 400
    with pytest.raises(HTTPException) as exc:
        await create_lab_order(
            order=schemas.LabOrderCreate(
                patient_id=patient.id,
                laboratory_id=lab.id,
                work_type="Overpaid Create",
                cost=Decimal("200.00"),
                paid_now=Decimal("250.00"),
            ),
            db=async_db_session,
            current_user=user,
        )
    assert exc.value.status_code == 400
    assert "يتجاوز" in exc.value.detail or "أكبر" in exc.value.detail

    # 2. Atomicity: force payment creation failure inside transaction
    orders_before = (
        await async_db_session.execute(
            sa.select(sa.func.count(models.LabOrder.id)).where(models.LabOrder.tenant_id == user.tenant_id)
        )
    ).scalar()

    # Simulate payment insert failure by monkeypatching session.add or raising error
    real_add = async_db_session.add

    def failing_add(instance):
        if isinstance(instance, models.LabPayment):
            raise RuntimeError("Forced payment insert failure")
        return real_add(instance)

    monkeypatch.setattr(async_db_session, "add", failing_add)

    with pytest.raises(RuntimeError, match="Forced payment insert failure"):
        await create_lab_order(
            order=schemas.LabOrderCreate(
                patient_id=patient.id,
                laboratory_id=lab.id,
                work_type="Failing Payment Order",
                cost=Decimal("200.00"),
                paid_now=Decimal("100.00"),
            ),
            db=async_db_session,
            current_user=user,
        )

    # Roll back the aborted transaction
    await async_db_session.rollback()

    orders_after = (
        await async_db_session.execute(
            sa.select(sa.func.count(models.LabOrder.id)).where(models.LabOrder.tenant_id == user.tenant_id)
        )
    ).scalar()
    assert orders_after == orders_before, "Order row must NOT exist when payment insert fails!"


# ---------------------------------------------------------------------------
# 7. Idempotent re-create does not double-pay
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_idempotent_recreate_does_not_double_pay(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    # Create treatment for idempotency anchor
    treatment = models.Treatment(
        patient_id=patient.id,
        procedure="Crown",
        cost=Decimal("1000.00"),
        tenant_id=user.tenant_id,
        doctor_id=user.id,
    )
    async_db_session.add(treatment)
    await async_db_session.flush()

    order_payload = schemas.LabOrderCreate(
        patient_id=patient.id,
        laboratory_id=lab.id,
        treatment_id=treatment.id,
        work_type="Crown",
        cost=Decimal("300.00"),
        paid_now=Decimal("100.00"),
    )

    # First submission: creates order + payment
    res1 = await create_lab_order(order=order_payload, db=async_db_session, current_user=user)
    assert res1["data"]["is_existing"] is False
    assert Decimal(str(res1["data"]["paid_amount"])) == Decimal("100.00")
    order_id = res1["data"]["id"]

    # Second submission: idempotent return, MUST NOT create second payment
    res2 = await create_lab_order(order=order_payload, db=async_db_session, current_user=user)
    assert res2["data"]["id"] == order_id
    assert res2["data"]["is_existing"] is True

    # Verify only 1 payment exists
    payments_count = (
        await async_db_session.execute(
            sa.select(sa.func.count(models.LabPayment.id)).where(
                models.LabPayment.lab_order_id == order_id,
                models.LabPayment.tenant_id == user.tenant_id,
            )
        )
    ).scalar()
    assert payments_count == 1


# ---------------------------------------------------------------------------
# 8. Delete with payments -> 409
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_lab_order_with_payments_returns_409(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    # Create order with paid_now
    res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Bridge",
            cost=Decimal("400.00"),
            paid_now=Decimal("100.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    order_id = res["data"]["id"]

    # Try to delete -> 409
    with pytest.raises(HTTPException) as exc:
        await delete_lab_order(order_id=order_id, db=async_db_session, current_user=user)
    assert exc.value.status_code == 409
    assert "الطلب عليه دفعات، الغِ الطلب بدل حذفه" in exc.value.detail

    # Delete order without payments -> succeeds
    res_no_pay = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Temporary",
            cost=Decimal("100.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    del_res = await delete_lab_order(
        order_id=res_no_pay["data"]["id"],
        db=async_db_session,
        current_user=user,
    )
    assert del_res["message"] == "Lab order deleted successfully"


# ---------------------------------------------------------------------------
# 9. Cost lowered below paid -> 400
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_cost_lowered_below_paid_returns_400(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Nightguard",
            cost=Decimal("300.00"),
            paid_now=Decimal("150.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    order_id = res["data"]["id"]

    # Try to lower cost to 100 (< 150) -> 400
    with pytest.raises(HTTPException) as exc:
        await update_lab_order(
            order_id=order_id,
            order_update=schemas.LabOrderUpdate(cost=Decimal("100.00")),
            db=async_db_session,
            current_user=user,
        )
    assert exc.value.status_code == 400
    assert "تقليل" in exc.value.detail or "أقل" in exc.value.detail

    # Lowering cost to 150 (== paid) -> succeeds
    ok_res = await update_lab_order(
        order_id=order_id,
        order_update=schemas.LabOrderUpdate(cost=Decimal("150.00")),
        db=async_db_session,
        current_user=user,
    )
    assert Decimal(str(ok_res["data"]["cost"])) == Decimal("150.00")
    assert Decimal(str(ok_res["data"]["remaining_amount"])) == Decimal("0.00")
    assert ok_res["data"]["payment_status"] == "paid"


# ---------------------------------------------------------------------------
# 10. Stats balance excludes cancelled and counts unpaid orders
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_stats_balance_excludes_cancelled_and_includes_unpaid_count(async_db_session, l1_setup):
    lab = l1_setup["lab"]
    patient = l1_setup["patient"]
    user = l1_setup["user"]

    # 1. Unpaid order: 250
    await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Order 1",
            cost=Decimal("250.00"),
        ),
        db=async_db_session,
        current_user=user,
    )

    # 2. Paid order: 200, paid 200
    await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Order 2",
            cost=Decimal("200.00"),
            paid_now=Decimal("200.00"),
        ),
        db=async_db_session,
        current_user=user,
    )

    # 3. Cancelled order: 300, paid 0
    res_c = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Order 3",
            cost=Decimal("300.00"),
        ),
        db=async_db_session,
        current_user=user,
    )
    await update_lab_order(
        order_id=res_c["data"]["id"],
        order_update=schemas.LabOrderUpdate(status="cancelled"),
        db=async_db_session,
        current_user=user,
    )

    # Check stats via router
    stats = await get_lab_stats(lab_id=lab.id, db=async_db_session, current_user=user)
    # total_cost must be 250 + 200 = 450 (300 excluded)
    assert stats["total_cost"] == 450.0
    assert stats["total_paid"] == 200.0
    # balance must be 450 - 200 = 250
    assert stats["balance"] == 250.0
    # unpaid_orders_count must be 1 (Order 1)
    assert stats["unpaid_orders_count"] == 1

    # Also verify LabService methods
    service = LabService(async_db_session, user.tenant_id)
    svc_stats = await service.get_lab_stats(lab.id)
    assert svc_stats["total_cost"] == 450.0
    assert svc_stats["total_paid"] == 200.0
    assert svc_stats["balance"] == 250.0
    assert svc_stats["unpaid_orders_count"] == 1


# ---------------------------------------------------------------------------
# 11. Alembic migration lifecycle (SQLite)
# ---------------------------------------------------------------------------
def test_alembic_lab_payment_order_link_migration_sqlite(monkeypatch):
    """Verify upgrade and downgrade of 7a8b9c0d1e2f on SQLite."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", sqlite_url)
        engine = sa.create_engine(sqlite_url)
        alembic_cfg_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        )
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        # 1. Base tables
        with engine.connect() as conn:
            conn.execute(sa.text("CREATE TABLE tenants (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text("CREATE TABLE laboratories (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(sa.text("CREATE TABLE lab_orders (id INTEGER PRIMARY KEY, tenant_id INTEGER)"))
            conn.execute(
                sa.text(
                    """CREATE TABLE lab_payments (
                        id INTEGER PRIMARY KEY,
                        laboratory_id INTEGER,
                        amount NUMERIC(14, 2),
                        date TIMESTAMP,
                        notes TEXT,
                        method VARCHAR,
                        tenant_id INTEGER
                    )"""
                )
            )
            conn.commit()

        # Stamp at 8b9c0d1e2f3a
        command.stamp(config, "8b9c0d1e2f3a")

        # Upgrade to 9c0d1e2f3a4b
        command.upgrade(config, "9c0d1e2f3a4b")

        inspector = sa.inspect(engine)
        cols = {c["name"]: c for c in inspector.get_columns("lab_payments")}
        assert "lab_order_id" in cols
        assert cols["lab_order_id"]["nullable"] is True

        indexes = {ix["name"] for ix in inspector.get_indexes("lab_payments")}
        assert "ix_lab_payments_lab_order_id" in indexes
        assert "ix_lab_payments_tenant_order" in indexes

        # Downgrade back to 8b9c0d1e2f3a
        command.downgrade(config, "8b9c0d1e2f3a")

        inspector_down = sa.inspect(engine)
        cols_down = {c["name"] for c in inspector_down.get_columns("lab_payments")}
        assert "lab_order_id" not in cols_down
        indexes_down = {ix["name"] for ix in inspector_down.get_indexes("lab_payments")}
        assert "ix_lab_payments_lab_order_id" not in indexes_down
        assert "ix_lab_payments_tenant_order" not in indexes_down

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


# ---------------------------------------------------------------------------
# 12. Import / Export round-trip test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_import_export_lab_orders_and_payments_roundtrip(async_db_session, test_user, test_patient):
    """Export and import must preserve lab debt and payment-order links."""
    tenant_id = test_user.tenant_id

    # Create lab
    lab = models.Laboratory(name="Export Lab", tenant_id=tenant_id, is_active=True)
    async_db_session.add(lab)
    await async_db_session.flush()

    # Create treatment
    treatment = models.Treatment(
        patient_id=test_patient.id,
        procedure="Crown",
        cost=Decimal("1200.00"),
        tenant_id=tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add(treatment)
    await async_db_session.flush()

    # Create 2 lab orders
    order1 = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        treatment_id=treatment.id,
        work_type="Crown",
        cost=Decimal("300.00"),
        price_to_patient=Decimal("1200.00"),
        tenant_id=tenant_id,
        doctor_id=test_user.id,
    )
    order2 = models.LabOrder(
        patient_id=test_patient.id,
        laboratory_id=lab.id,
        work_type="Bridge",
        cost=Decimal("500.00"),
        tenant_id=tenant_id,
        doctor_id=test_user.id,
    )
    async_db_session.add_all([order1, order2])
    await async_db_session.flush()

    # Create payments: one linked to order1, one on-account (unlinked)
    pay1 = models.LabPayment(
        laboratory_id=lab.id,
        lab_order_id=order1.id,
        amount=Decimal("100.00"),
        tenant_id=tenant_id,
    )
    pay2 = models.LabPayment(
        laboratory_id=lab.id,
        lab_order_id=None,
        amount=Decimal("50.00"),
        tenant_id=tenant_id,
    )
    async_db_session.add_all([pay1, pay2])
    await async_db_session.commit()

    # Export
    export_payload = await export_tenant_data(async_db_session, tenant_id)
    assert len(export_payload["data"]["lab_orders"]) == 2
    assert len(export_payload["data"]["lab_payments"]) == 2

    # Create target tenant for clean restore
    target_tenant = models.Tenant(name="Restore Target Tenant", is_active=True)
    async_db_session.add(target_tenant)
    await async_db_session.commit()

    # Avoid global email collision across tenants in test environment
    for u in export_payload["data"].get("users", []):
        if "email" in u and u["email"]:
            u["email"] = f"target_{u['email']}"
        if "username" in u and u["username"]:
            u["username"] = f"target_{u['username']}"

    # Restore into target tenant
    await import_tenant_data(async_db_session, target_tenant.id, export_payload)

    # Verify restored data in target tenant
    restored_orders = (
        await async_db_session.execute(
            sa.select(models.LabOrder).where(models.LabOrder.tenant_id == target_tenant.id).order_by(models.LabOrder.id)
        )
    ).scalars().all()
    assert len(restored_orders) == 2

    crown_order = next(o for o in restored_orders if o.work_type == "Crown")
    bridge_order = next(o for o in restored_orders if o.work_type == "Bridge")
    assert crown_order.treatment_id is not None, "treatment_id must be remapped"
    assert bridge_order.treatment_id is None

    restored_payments = (
        await async_db_session.execute(
            sa.select(models.LabPayment).where(models.LabPayment.tenant_id == target_tenant.id).order_by(models.LabPayment.id)
        )
    ).scalars().all()
    assert len(restored_payments) == 2

    # Verify link remapping: pay1 linked to restored_order1, pay2 unlinked
    linked_pays = [p for p in restored_payments if p.lab_order_id is not None]
    unlinked_pays = [p for p in restored_payments if p.lab_order_id is None]
    assert len(linked_pays) == 1
    assert len(unlinked_pays) == 1
    assert linked_pays[0].lab_order_id == crown_order.id
    assert Decimal(str(linked_pays[0].amount)) == Decimal("100.00")
