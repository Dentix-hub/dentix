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
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend import models, schemas
from backend.database import AsyncSessionLocal, RlsContext
from backend.routers.laboratories import create_lab_payment, allocate_lab_payment

TENANT_ID = 99840
USER_ID = 998401
PATIENT_ID = 998402
LAB_ID = 998403


async def _seed() -> models.User:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            user = await db.get(models.User, USER_ID)
            if user is not None:
                return user

            tenant = models.Tenant(id=TENANT_ID, name="Lab Concurrency Postgres Tenant", is_active=True)
            db.add(tenant)
            await db.flush()

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
