"""Real PostgreSQL concurrency test for Lab Order Payments (Slice L1).

Proves:
1. Two simultaneous payment requests against the same LabOrder serialize via
   row-level locking (SELECT ... FOR UPDATE).
2. Exactly one payment succeeds and the other is rejected with HTTP 400 (amount exceeds remaining).
3. The total amount paid never exceeds the order cost.
4. The test is discriminating: without row locking, two simultaneous transactions
   can both read stale remaining balance and overpay the order.
"""

import asyncio
from decimal import Decimal
from itertools import product
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text

from backend import models, schemas
from backend.database import AsyncSessionLocal, RlsContext, system_async_engine
from backend.routers.laboratories import create_lab_payment, allocate_lab_payment, update_lab_order
from backend.services.lab_service import LabService

TENANT_ID = 99840
USER_ID = 998401
PATIENT_ID = 998402
LAB_ID = 998403


async def _seed() -> models.User:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            tenant = await db.get(models.Tenant, TENANT_ID)
            if tenant is None:
                tenant = models.Tenant(id=TENANT_ID, name="Lab Concurrency Postgres Tenant", is_active=True)
                db.add(tenant)
                await db.flush()

            admin = await db.get(models.User, USER_ID)
            if admin is None:
                admin = models.User(
                    id=USER_ID,
                    tenant_id=TENANT_ID,
                    username="lab_concurrency_admin",
                    email="lab_concurrency_admin@example.com",
                    hashed_password="fakepassword",
                    role="admin",
                    is_active=True,
                )
                db.add(admin)
                await db.flush()

            patient = await db.get(models.Patient, PATIENT_ID)
            if patient is None:
                patient = models.Patient(
                    id=PATIENT_ID,
                    tenant_id=TENANT_ID,
                    name="Lab Concurrency Patient",
                    age=32,
                    medical_history="None",
                    notes="",
                    phone="01099840001",
                )
                db.add(patient)

            lab = await db.get(models.Laboratory, LAB_ID)
            if lab is None:
                lab = models.Laboratory(
                    id=LAB_ID,
                    tenant_id=TENANT_ID,
                    name="Postgres Concurrency Lab",
                    phone="01099840002",
                    is_active=True,
                )
                db.add(lab)
            await db.commit()
            return admin


@pytest.mark.asyncio
async def test_concurrent_payments_never_exceed_order_cost():
    """Two concurrent payments of 150 against a 200 order must serialize.

    One must win and one must fail with HTTP 400. Total paid must equal 150 <= 200.
    """
    user = await _seed()

    # Create order with cost 200 in a clean transaction
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        order = models.LabOrder(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            doctor_id=USER_ID,
            laboratory_id=LAB_ID,
            work_type="Zirconia Crown",
            cost=Decimal("200.00"),
            price_to_patient=Decimal("600.00"),
            status="pending",
        )
        session.add(order)
        await session.commit()
        order_id = order.id

    barrier = asyncio.Barrier(2)

    async def worker(worker_num: int):
        await barrier.wait()
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
            payload = schemas.LabPaymentCreate(
                laboratory_id=LAB_ID,
                lab_order_id=order_id,
                amount=Decimal("150.00"),
                method="Cash",
                notes=f"Worker {worker_num}",
            )
            return await create_lab_payment(
                lab_id=LAB_ID,
                payment=payload,
                db=session,
                current_user=user,
            )

    results = await asyncio.gather(worker(1), worker(2), return_exceptions=True)

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}: {results}"

    failure = failures[0]
    assert isinstance(failure, HTTPException), f"Expected HTTPException, got {type(failure)}: {failure}"
    assert failure.status_code == 400
    assert "يتجاوز" in failure.detail or "المتبقي" in failure.detail

    # Verify invariants on PostgreSQL
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        stmt_pay = select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
            models.LabPayment.tenant_id == TENANT_ID,
            models.LabPayment.lab_order_id == order_id,
        )
        total_paid = (await session.execute(stmt_pay)).scalar()
        assert Decimal(str(total_paid)) == Decimal("150.00")

        # Verify only 1 payment row exists
        count = (
            await session.execute(
                select(func.count(models.LabPayment.id)).where(
                    models.LabPayment.tenant_id == TENANT_ID,
                    models.LabPayment.lab_order_id == order_id,
                )
            )
        ).scalar()
        assert count == 1


@pytest.mark.asyncio
async def test_concurrency_lock_is_discriminating():
    """Proves the lock is discriminating: without row locking, race conditions cause overpayment."""
    await _seed()

    # Create order with cost 200
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        order = models.LabOrder(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            doctor_id=USER_ID,
            laboratory_id=LAB_ID,
            work_type="Test Lock Overpay",
            cost=Decimal("200.00"),
            status="pending",
        )
        session.add(order)
        await session.commit()
        order_id = order.id

    barrier = asyncio.Barrier(2)

    # Simulate workers doing check-then-act WITHOUT row-locking
    async def worker_without_lock(worker_num: int):
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
            # Query WITHOUT with_for_update()
            ord_row = (
                await session.execute(
                    select(models.LabOrder).where(models.LabOrder.id == order_id)
                )
            ).scalars().first()

            paid_sum = (
                await session.scalar(
                    select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
                        models.LabPayment.lab_order_id == order_id
                    )
                )
            ) or 0
            remaining = ord_row.cost - paid_sum

            # Synchronize both workers right after reading the same stale remaining balance
            await barrier.wait()

            amount_to_pay = Decimal("150.00")
            if amount_to_pay <= remaining:
                # Both workers see remaining == 200 and insert 150
                p = models.LabPayment(
                    tenant_id=TENANT_ID,
                    laboratory_id=LAB_ID,
                    lab_order_id=order_id,
                    amount=amount_to_pay,
                    notes=f"No-lock worker {worker_num}",
                )
                session.add(p)
                await session.commit()
                return p
            raise HTTPException(status_code=400, detail="Overpay")

    results = await asyncio.gather(
        worker_without_lock(1), worker_without_lock(2), return_exceptions=True
    )

    # Without locking, BOTH workers succeed
    no_lock_successes = [r for r in results if not isinstance(r, Exception)]
    assert len(no_lock_successes) == 2, "Without lock, both workers should have succeeded (race condition)"

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        overpay_sum = await session.scalar(
            select(func.sum(models.LabPayment.amount)).where(
                models.LabPayment.lab_order_id == order_id
            )
        )
        # Without lock, total paid became 300, exceeding order cost 200!
        assert Decimal(str(overpay_sum)) == Decimal("300.00")


@pytest.mark.asyncio
async def test_concurrent_allocations_never_exceed_order_cost():
    """Two concurrent allocations of 150 payments against a 200 order must serialize.

    One must win and one must fail with HTTP 400. Total paid must equal 150 <= 200.
    """
    user = await _seed()

    # Create order with cost 200 and two unlinked payments of 150 each
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        order = models.LabOrder(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            doctor_id=USER_ID,
            laboratory_id=LAB_ID,
            work_type="Zirconia Crown Concurrent Alloc",
            cost=Decimal("200.00"),
            price_to_patient=Decimal("600.00"),
            status="pending",
        )
        session.add(order)
        await session.flush()
        order_id = order.id

        pay1 = models.LabPayment(
            tenant_id=TENANT_ID,
            laboratory_id=LAB_ID,
            lab_order_id=None,
            amount=Decimal("150.00"),
            method="Cash",
            notes="Alloc Worker 1",
        )
        pay2 = models.LabPayment(
            tenant_id=TENANT_ID,
            laboratory_id=LAB_ID,
            lab_order_id=None,
            amount=Decimal("150.00"),
            method="Cash",
            notes="Alloc Worker 2",
        )
        session.add_all([pay1, pay2])
        await session.commit()
        pay1_id = pay1.id
        pay2_id = pay2.id

    barrier = asyncio.Barrier(2)

    async def worker(payment_id: int):
        await barrier.wait()
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
            payload = schemas.LabPaymentAllocate(lab_order_id=order_id)
            return await allocate_lab_payment(
                lab_id=LAB_ID,
                payment_id=payment_id,
                payload=payload,
                db=session,
                current_user=user,
            )

    results = await asyncio.gather(worker(pay1_id), worker(pay2_id), return_exceptions=True)

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}: {results}"

    failure = failures[0]
    assert isinstance(failure, HTTPException), f"Expected HTTPException, got {type(failure)}: {failure}"
    assert failure.status_code == 400
    assert "يتجاوز" in failure.detail or "المتبقي" in failure.detail

    # Verify invariants on PostgreSQL
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        stmt_pay = select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
            models.LabPayment.tenant_id == TENANT_ID,
            models.LabPayment.lab_order_id == order_id,
        )
        total_paid = (await session.execute(stmt_pay)).scalar()
        assert Decimal(str(total_paid)) == Decimal("150.00")

        # Verify exactly 1 payment is linked to the order
        count = (
            await session.execute(
                select(func.count(models.LabPayment.id)).where(
                    models.LabPayment.tenant_id == TENANT_ID,
                    models.LabPayment.lab_order_id == order_id,
                )
            )
        ).scalar()
        assert count == 1


async def _new_cost_race_order():
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as db:
        order = models.LabOrder(
            tenant_id=TENANT_ID, patient_id=PATIENT_ID, laboratory_id=LAB_ID,
            work_type="Cost/payment serialization", cost=Decimal("100.00"),
            price_to_patient=Decimal("0.00"), status="pending",
        )
        db.add(order)
        await db.commit()
        return order.id


async def _edit_order_cost(db, user, order_id, path):
    payload = schemas.LabOrderUpdate(cost=Decimal("50.00"))
    if path == "router":
        return await update_lab_order(order_id=order_id, order_update=payload, db=db, current_user=user)
    return await LabService(db, TENANT_ID).update_lab_order(order_id, payload)


async def _record_order_payment(db, user, order_id, path, payment_id):
    if path.endswith("allocate"):
        if path.startswith("router"):
            return await allocate_lab_payment(
                lab_id=LAB_ID, payment_id=payment_id,
                payload=schemas.LabPaymentAllocate(lab_order_id=order_id), db=db, current_user=user,
            )
        return await LabService(db, TENANT_ID).allocate_payment(LAB_ID, payment_id, order_id)
    payload = schemas.LabPaymentCreate(
        laboratory_id=LAB_ID, lab_order_id=order_id, amount=Decimal("100.00"), method="Cash",
    )
    if path.startswith("router"):
        return await create_lab_payment(lab_id=LAB_ID, payment=payload, db=db, current_user=user)
    return await LabService(db, TENANT_ID).create_lab_payment(LAB_ID, payload)


def _pause_after_payment_total(monkeypatch, db, reached, release):
    scalar = db.scalar

    async def paused(statement, *args, **kwargs):
        value = await scalar(statement, *args, **kwargs)
        if "sum(lab_payments.amount)" in str(statement):
            reached.set()
            await asyncio.wait_for(release.wait(), timeout=15)
        return value

    monkeypatch.setattr(db, "scalar", paused)


async def _assert_database_waiter(task, waiter_pid, holder_pid):
    """Observe the real PostgreSQL lock, rather than guessing with a sleep."""
    async with system_async_engine.connect() as observer:
        async def wait():
            while True:
                blockers = await observer.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": waiter_pid})
                if holder_pid in blockers:
                    return
                assert not task.done(), "Competing operation completed before the order lock was released"
                await asyncio.sleep(0.01)

        await asyncio.wait_for(wait(), timeout=10)


_COST_PAYMENT_CASES = list(product(
    ["router", "service"],
    ["router_create", "router_allocate", "service_create", "service_allocate"],
    ["payment", "cost"],
))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "update_path,payment_path,winner", _COST_PAYMENT_CASES,
    ids=[f"{winner}-{update}-{payment}" for update, payment, winner in _COST_PAYMENT_CASES],
)
async def test_cost_edits_serialize_with_payments(monkeypatch, update_path, payment_path, winner):
    """Both lock orders preserve paid <= cost, including preloaded ORM objects."""
    user = await _seed()
    order_id = await _new_cost_race_order()
    payment_id = None
    if payment_path.endswith("allocate"):
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as db:
            payment = models.LabPayment(tenant_id=TENANT_ID, laboratory_id=LAB_ID, amount=Decimal("100.00"))
            db.add(payment)
            await db.commit()
            payment_id = payment.id

    reached, release = asyncio.Event(), asyncio.Event()
    async with (
        AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as update_db,
        AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as payment_db,
    ):
        # Keep strong references so the identity map really contains stale data
        # when the other transaction commits a new cost.
        cached_orders = [
            (await db.execute(select(models.LabOrder).where(
                models.LabOrder.id == order_id, models.LabOrder.tenant_id == TENANT_ID,
            ))).scalar_one()
            for db in (update_db, payment_db)
        ]
        assert all(order.cost == Decimal("100.00") for order in cached_orders)
        update_pid = await update_db.scalar(text("SELECT pg_backend_pid()"))
        payment_pid = await payment_db.scalar(text("SELECT pg_backend_pid()"))
        holder, holder_pid, waiter_pid = (
            (payment_db, payment_pid, update_pid) if winner == "payment"
            else (update_db, update_pid, payment_pid)
        )
        _pause_after_payment_total(monkeypatch, holder, reached, release)
        actions = {
            "cost": lambda: _edit_order_cost(update_db, user, order_id, update_path),
            "payment": lambda: _record_order_payment(payment_db, user, order_id, payment_path, payment_id),
        }
        other = "cost" if winner == "payment" else "payment"
        tasks = [asyncio.create_task(actions[winner]())]
        try:
            await asyncio.wait_for(reached.wait(), timeout=10)
            tasks.append(asyncio.create_task(actions[other]()))
            await _assert_database_waiter(tasks[1], waiter_pid, holder_pid)
        finally:
            release.set()
            results = await asyncio.gather(*tasks, return_exceptions=True)
        assert not isinstance(results[0], Exception), results[0]
        failure = results[1]
        rejected_path = update_path if other == "cost" else payment_path
        if rejected_path.startswith("router"):
            assert isinstance(failure, HTTPException), results
            assert failure.status_code == 400
            message = failure.detail
        else:
            assert isinstance(failure, ValueError), results
            message = str(failure)
        assert ("أقل" if other == "cost" else "يتجاوز") in message

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as db:
        cost = await db.scalar(select(models.LabOrder.cost).where(
            models.LabOrder.id == order_id, models.LabOrder.tenant_id == TENANT_ID,
        ))
        paid = await db.scalar(select(func.coalesce(func.sum(models.LabPayment.amount), 0)).where(
            models.LabPayment.lab_order_id == order_id, models.LabPayment.tenant_id == TENANT_ID,
        ))
        assert paid <= cost
        assert (cost, paid) == (
            (Decimal("100.00"), Decimal("100.00")) if winner == "payment"
            else (Decimal("50.00"), Decimal("0.00"))
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("update_path", ["router", "service"])
async def test_cost_edit_does_not_block_payment_to_another_order(monkeypatch, update_path):
    user = await _seed()
    order_id, other_order_id = await _new_cost_race_order(), await _new_cost_race_order()
    reached, release = asyncio.Event(), asyncio.Event()
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as update_db:
        _pause_after_payment_total(monkeypatch, update_db, reached, release)
        task = asyncio.create_task(_edit_order_cost(update_db, user, order_id, update_path))
        try:
            await asyncio.wait_for(reached.wait(), timeout=10)
            async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as payment_db:
                await asyncio.wait_for(
                    _record_order_payment(payment_db, user, other_order_id, "router_create", None), timeout=10,
                )
        finally:
            release.set()
            await task
