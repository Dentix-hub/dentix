"""Tests for PR-1: Lab Payment Allocation to Lab Orders.

Covers:
1. Happy path: allocate an existing unlinked payment to an order.
2. Already-linked payment rejected with 409 («الدفعة مرتبطة بطلب بالفعل»).
3. Cross-tenant order rejected (404) and cross-lab order rejected (400).
4. Amount > remaining rejected (400 with remaining amount in Arabic).
5. Cancelled order rejected (400).
6. Financial invariants: finance summary lab_costs and activity feed identical before/after allocation.
7. Undo (deallocation) works (sets lab_order_id = NULL) and 404 if not linked.
8. Lab stats fields (unallocated_payments_total, unallocated_payments_count).
9. Audit log entry recorded on allocate and deallocate.
10. Permission enforcement (FINANCIAL_WRITE required).
"""

from decimal import Decimal
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException

from backend import models, schemas
from backend.core.money import quantize_money
from backend.routers.laboratories import (
    create_lab_order,
    create_lab_payment,
    get_lab_order,
    get_lab_stats,
    update_lab_order,
)
try:
    from backend.routers.laboratories import (
        allocate_lab_payment,
        deallocate_lab_payment,
    )
except ImportError:
    allocate_lab_payment = None
    deallocate_lab_payment = None

from backend.services.accounting_service import AccountingService
from backend.services.finance_summary_service import FinanceSummaryService


@pytest.fixture
async def pr1_setup(async_db_session, test_user, test_patient):
    """Seed test clinic laboratory, patient, and users."""
    tenant_id = test_user.tenant_id
    lab = models.Laboratory(
        name="Al-Noor Dental Lab",
        phone="01011223344",
        tenant_id=tenant_id,
        is_active=True,
    )
    async_db_session.add(lab)
    await async_db_session.flush()

    admin = models.User(
        username="pr1_admin_user",
        email="admin_pr1@example.com",
        hashed_password="fakepassword",
        role="admin",
        tenant_id=tenant_id,
        is_active=True,
    )
    receptionist = models.User(
        username="pr1_receptionist",
        email="receptionist@example.com",
        hashed_password="fakepassword",
        role="receptionist",
        tenant_id=tenant_id,
        is_active=True,
    )
    async_db_session.add_all([admin, receptionist])
    await async_db_session.commit()
    await async_db_session.refresh(lab)
    await async_db_session.refresh(admin)
    await async_db_session.refresh(receptionist)

    return {
        "lab": lab,
        "patient": test_patient,
        "admin": admin,
        "receptionist": receptionist,
        "tenant_id": tenant_id,
    }


# ---------------------------------------------------------------------------
# 1. Happy path: allocate existing unlinked payment to order
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_allocate_payment_happy_path(async_db_session, pr1_setup):
    lab = pr1_setup["lab"]
    patient = pr1_setup["patient"]
    admin = pr1_setup["admin"]

    # 1. Create order for 300
    order_res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Zirconia Crown",
            cost=Decimal("300.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    order_id = order_res["data"]["id"]

    # 2. Create unlinked payment («على الحساب») of 150
    pay_res = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=None,
            amount=Decimal("150.00"),
            method="Cash",
            notes="دفعة على الحساب",
        ),
        db=async_db_session,
        current_user=admin,
    )
    payment_id = pay_res["data"].id if hasattr(pay_res["data"], "id") else pay_res["data"]["id"]

    # Order is unpaid before allocation
    order_before = (await get_lab_order(order_id=order_id, db=async_db_session, current_user=admin))["data"]
    assert order_before["payment_status"] == "unpaid"
    assert Decimal(str(order_before["paid_amount"])) == Decimal("0.00")
    assert Decimal(str(order_before["remaining_amount"])) == Decimal("300.00")

    # 3. Allocate payment to order
    assert allocate_lab_payment is not None, "allocate_lab_payment route handler must be implemented"
    alloc_res = await allocate_lab_payment(
        lab_id=lab.id,
        payment_id=payment_id,
        payload=schemas.LabPaymentAllocate(lab_order_id=order_id),
        db=async_db_session,
        current_user=admin,
    )
    alloc_data = alloc_res["data"] if isinstance(alloc_res, dict) else alloc_res
    alloc_order_id = alloc_data.lab_order_id if hasattr(alloc_data, "lab_order_id") else alloc_data["lab_order_id"]
    assert alloc_order_id == order_id

    # 4. Order is now partial: paid 150, remaining 150
    order_after = (await get_lab_order(order_id=order_id, db=async_db_session, current_user=admin))["data"]
    assert order_after["payment_status"] == "partial"
    assert Decimal(str(order_after["paid_amount"])) == Decimal("150.00")
    assert Decimal(str(order_after["remaining_amount"])) == Decimal("150.00")

    # 5. Verify audit log entry
    from sqlalchemy import select
    audit_stmt = (
        select(models.AuditLog)
        .where(
            models.AuditLog.tenant_id == pr1_setup["tenant_id"],
            models.AuditLog.action == "allocate",
            models.AuditLog.entity_type == "lab_payment",
            models.AuditLog.entity_id == payment_id,
        )
    )
    audit_entry = (await async_db_session.execute(audit_stmt)).scalars().first()
    assert audit_entry is not None
    assert str(order_id) in audit_entry.details or f"#{order_id}" in audit_entry.details


# ---------------------------------------------------------------------------
# 2. Already-linked payment rejected with 409
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_allocate_already_linked_payment_rejected_409(async_db_session, pr1_setup):
    lab = pr1_setup["lab"]
    patient = pr1_setup["patient"]
    admin = pr1_setup["admin"]

    # Order 1
    ord1 = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Crown 1",
            cost=Decimal("200.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    ord1_id = ord1["data"]["id"]

    # Order 2
    ord2 = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Crown 2",
            cost=Decimal("200.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    ord2_id = ord2["data"]["id"]

    # Payment linked to Order 1 at creation
    pay_res = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=ord1_id,
            amount=Decimal("100.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    payment_id = pay_res["data"].id if hasattr(pay_res["data"], "id") else pay_res["data"]["id"]

    # Attempt to allocate already-linked payment to Order 2 -> 409
    assert allocate_lab_payment is not None, "allocate_lab_payment route handler must be implemented"
    with pytest.raises(HTTPException) as exc:
        await allocate_lab_payment(
            lab_id=lab.id,
            payment_id=payment_id,
            payload=schemas.LabPaymentAllocate(lab_order_id=ord2_id),
            db=async_db_session,
            current_user=admin,
        )
    assert exc.value.status_code == 409
    assert "مرتبطة بطلب بالفعل" in exc.value.detail


# ---------------------------------------------------------------------------
# 3. Cross-tenant and cross-lab order rejected
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_allocate_cross_tenant_and_cross_lab_rejected(async_db_session, pr1_setup):
    lab = pr1_setup["lab"]
    patient = pr1_setup["patient"]
    admin = pr1_setup["admin"]
    tenant_id = pr1_setup["tenant_id"]

    # Payment in lab
    pay_res = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=None,
            amount=Decimal("100.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    payment_id = pay_res["data"].id if hasattr(pay_res["data"], "id") else pay_res["data"]["id"]

    # Lab 2 in same tenant
    lab2 = models.Laboratory(name="Other Lab Same Tenant", tenant_id=tenant_id, is_active=True)
    async_db_session.add(lab2)
    await async_db_session.flush()

    order_lab2 = models.LabOrder(
        patient_id=patient.id,
        laboratory_id=lab2.id,
        work_type="Bridge",
        cost=Decimal("200.00"),
        tenant_id=tenant_id,
    )
    async_db_session.add(order_lab2)

    # Other tenant
    other_tenant = models.Tenant(name="Foreign Clinic", is_active=True)
    async_db_session.add(other_tenant)
    await async_db_session.flush()

    foreign_patient = models.Patient(
        name="Foreign Patient",
        age=25,
        medical_history="None",
        notes="",
        tenant_id=other_tenant.id,
        phone="0122222222",
        is_deleted=False,
    )
    foreign_lab = models.Laboratory(name="Foreign Lab", tenant_id=other_tenant.id, is_active=True)
    async_db_session.add_all([foreign_patient, foreign_lab])
    await async_db_session.flush()

    foreign_order = models.LabOrder(
        patient_id=foreign_patient.id,
        laboratory_id=foreign_lab.id,
        work_type="Implant",
        cost=Decimal("200.00"),
        tenant_id=other_tenant.id,
    )
    async_db_session.add(foreign_order)
    await async_db_session.commit()

    assert allocate_lab_payment is not None, "allocate_lab_payment route handler must be implemented"

    # Cross-tenant order -> 404
    with pytest.raises(HTTPException) as exc_tenant:
        await allocate_lab_payment(
            lab_id=lab.id,
            payment_id=payment_id,
            payload=schemas.LabPaymentAllocate(lab_order_id=foreign_order.id),
            db=async_db_session,
            current_user=admin,
        )
    assert exc_tenant.value.status_code == 404

    # Cross-lab order -> 400
    with pytest.raises(HTTPException) as exc_lab:
        await allocate_lab_payment(
            lab_id=lab.id,
            payment_id=payment_id,
            payload=schemas.LabPaymentAllocate(lab_order_id=order_lab2.id),
            db=async_db_session,
            current_user=admin,
        )
    assert exc_lab.value.status_code == 400
    assert "لا يتبع هذا المعمل" in exc_lab.value.detail or "المعمل" in exc_lab.value.detail


# ---------------------------------------------------------------------------
# 4. Payment amount > order remaining rejected (400 with remaining in Arabic)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_allocate_amount_exceeds_remaining_rejected(async_db_session, pr1_setup):
    lab = pr1_setup["lab"]
    patient = pr1_setup["patient"]
    admin = pr1_setup["admin"]

    # Order of 100
    order_res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Inlay",
            cost=Decimal("100.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    order_id = order_res["data"]["id"]

    # Payment of 150 (150 > 100)
    pay_res = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=None,
            amount=Decimal("150.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    payment_id = pay_res["data"].id if hasattr(pay_res["data"], "id") else pay_res["data"]["id"]

    assert allocate_lab_payment is not None, "allocate_lab_payment route handler must be implemented"
    with pytest.raises(HTTPException) as exc:
        await allocate_lab_payment(
            lab_id=lab.id,
            payment_id=payment_id,
            payload=schemas.LabPaymentAllocate(lab_order_id=order_id),
            db=async_db_session,
            current_user=admin,
        )
    assert exc.value.status_code == 400
    assert "يتجاوز" in exc.value.detail or "المتبقي" in exc.value.detail
    assert "100.00" in exc.value.detail or "100" in exc.value.detail


# ---------------------------------------------------------------------------
# 5. Cancelled order rejected (400)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_allocate_cancelled_order_rejected(async_db_session, pr1_setup):
    lab = pr1_setup["lab"]
    patient = pr1_setup["patient"]
    admin = pr1_setup["admin"]

    order_res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Cancelled Work",
            cost=Decimal("200.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    order_id = order_res["data"]["id"]

    await update_lab_order(
        order_id=order_id,
        order_update=schemas.LabOrderUpdate(status="cancelled"),
        db=async_db_session,
        current_user=admin,
    )

    pay_res = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=None,
            amount=Decimal("100.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    payment_id = pay_res["data"].id if hasattr(pay_res["data"], "id") else pay_res["data"]["id"]

    assert allocate_lab_payment is not None, "allocate_lab_payment route handler must be implemented"
    with pytest.raises(HTTPException) as exc:
        await allocate_lab_payment(
            lab_id=lab.id,
            payment_id=payment_id,
            payload=schemas.LabPaymentAllocate(lab_order_id=order_id),
            db=async_db_session,
            current_user=admin,
        )
    assert exc.value.status_code == 400
    assert "ملغي" in exc.value.detail


# ---------------------------------------------------------------------------
# 6. Finance summary lab_costs and activity feed identical before/after allocation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_finance_summary_and_activity_feed_identical_before_after_allocation(
    async_db_session, pr1_setup
):
    lab = pr1_setup["lab"]
    patient = pr1_setup["patient"]
    admin = pr1_setup["admin"]
    tenant_id = pr1_setup["tenant_id"]

    order_res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Zirconia Case",
            cost=Decimal("500.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    order_id = order_res["data"]["id"]

    pay_res = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=None,
            amount=Decimal("200.00"),
            notes="دفعة على الحساب",
        ),
        db=async_db_session,
        current_user=admin,
    )
    payment_id = pay_res["data"].id if hasattr(pay_res["data"], "id") else pay_res["data"]["id"]

    summary_svc = FinanceSummaryService(async_db_session, tenant_id)
    accounting = AccountingService(async_db_session, tenant_id)

    # 1. Capture BEFORE allocation
    summary_before = await summary_svc.get_summary()
    activity_before = await accounting.get_financial_activity(
        event_types=["lab"],
        current_user=admin,
    )

    # 2. Allocate payment to order
    assert allocate_lab_payment is not None, "allocate_lab_payment route handler must be implemented"
    await allocate_lab_payment(
        lab_id=lab.id,
        payment_id=payment_id,
        payload=schemas.LabPaymentAllocate(lab_order_id=order_id),
        db=async_db_session,
        current_user=admin,
    )

    # 3. Capture AFTER allocation
    summary_after = await summary_svc.get_summary()
    activity_after = await accounting.get_financial_activity(
        event_types=["lab"],
        current_user=admin,
    )

    # Invariants: lab_costs and lab_debt stay 100% identical!
    assert summary_before["deductions"]["lab_costs"] == summary_after["deductions"]["lab_costs"]
    assert summary_before["deductions"]["total_deductions"] == summary_after["deductions"]["total_deductions"]
    assert summary_before["obligations"]["lab_debt"] == summary_after["obligations"]["lab_debt"]
    assert summary_before["net_operational_result"] == summary_after["net_operational_result"]

    # Activity feed metrics stay identical
    assert activity_before["total_count"] == activity_after["total_count"]
    assert activity_before["total_outflow"] == activity_after["total_outflow"]
    assert activity_before["net_flow"] == activity_after["net_flow"]
    assert len(activity_before["events"]) == len(activity_after["events"])
    assert activity_before["events"][0]["amount"] == activity_after["events"][0]["amount"]


# ---------------------------------------------------------------------------
# 7. Undo works (deallocation sets lab_order_id = NULL) & 404 if not linked
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_undo_deallocation_works_and_unlinked_404(async_db_session, pr1_setup):
    lab = pr1_setup["lab"]
    patient = pr1_setup["patient"]
    admin = pr1_setup["admin"]

    order_res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Crown Test",
            cost=Decimal("250.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    order_id = order_res["data"]["id"]

    pay_res = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=None,
            amount=Decimal("100.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    payment_id = pay_res["data"].id if hasattr(pay_res["data"], "id") else pay_res["data"]["id"]

    assert deallocate_lab_payment is not None, "deallocate_lab_payment route handler must be implemented"

    # Attempting undo before allocation -> 404
    with pytest.raises(HTTPException) as exc_unlinked:
        await deallocate_lab_payment(
            lab_id=lab.id,
            payment_id=payment_id,
            db=async_db_session,
            current_user=admin,
        )
    assert exc_unlinked.value.status_code == 404

    # Allocate
    await allocate_lab_payment(
        lab_id=lab.id,
        payment_id=payment_id,
        payload=schemas.LabPaymentAllocate(lab_order_id=order_id),
        db=async_db_session,
        current_user=admin,
    )

    # Undo allocation
    undo_res = await deallocate_lab_payment(
        lab_id=lab.id,
        payment_id=payment_id,
        db=async_db_session,
        current_user=admin,
    )
    undo_data = undo_res["data"] if isinstance(undo_res, dict) else undo_res
    undo_order_id = undo_data.lab_order_id if hasattr(undo_data, "lab_order_id") else undo_data["lab_order_id"]
    assert undo_order_id is None

    # Order returns to unpaid
    order_unlinked = (await get_lab_order(order_id=order_id, db=async_db_session, current_user=admin))["data"]
    assert order_unlinked["payment_status"] == "unpaid"
    assert Decimal(str(order_unlinked["paid_amount"])) == Decimal("0.00")
    assert Decimal(str(order_unlinked["remaining_amount"])) == Decimal("250.00")

    # Verify audit log entry for deallocate
    from sqlalchemy import select
    audit_stmt = (
        select(models.AuditLog)
        .where(
            models.AuditLog.tenant_id == pr1_setup["tenant_id"],
            models.AuditLog.action == "deallocate",
            models.AuditLog.entity_type == "lab_payment",
            models.AuditLog.entity_id == payment_id,
        )
    )
    audit_entry = (await async_db_session.execute(audit_stmt)).scalars().first()
    assert audit_entry is not None


# ---------------------------------------------------------------------------
# 8. Lab stats fields (unallocated_payments_total, unallocated_payments_count)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_lab_stats_unallocated_fields(async_db_session, pr1_setup):
    lab = pr1_setup["lab"]
    patient = pr1_setup["patient"]
    admin = pr1_setup["admin"]

    # Create order
    ord_res = await create_lab_order(
        order=schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=lab.id,
            work_type="Veneer Case",
            cost=Decimal("400.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    order_id = ord_res["data"]["id"]

    # 1. Linked payment of 100
    await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=order_id,
            amount=Decimal("100.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )

    # 2. Two unlinked payments of 150 and 50
    pay_unlinked1 = await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=None,
            amount=Decimal("150.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )
    p1_id = pay_unlinked1["data"].id if hasattr(pay_unlinked1["data"], "id") else pay_unlinked1["data"]["id"]

    await create_lab_payment(
        lab_id=lab.id,
        payment=schemas.LabPaymentCreate(
            laboratory_id=lab.id,
            lab_order_id=None,
            amount=Decimal("50.00"),
        ),
        db=async_db_session,
        current_user=admin,
    )

    stats = await get_lab_stats(lab_id=lab.id, db=async_db_session, current_user=admin)
    assert stats["unallocated_payments_total"] == 200.0
    assert stats["unallocated_payments_count"] == 2

    # Allocate 150 to order
    assert allocate_lab_payment is not None
    await allocate_lab_payment(
        lab_id=lab.id,
        payment_id=p1_id,
        payload=schemas.LabPaymentAllocate(lab_order_id=order_id),
        db=async_db_session,
        current_user=admin,
    )

    stats_after = await get_lab_stats(lab_id=lab.id, db=async_db_session, current_user=admin)
    assert stats_after["unallocated_payments_total"] == 50.0
    assert stats_after["unallocated_payments_count"] == 1


# ---------------------------------------------------------------------------
# 9. Permission check: FINANCIAL_WRITE required
# ---------------------------------------------------------------------------
def test_allocate_permission_required():
    from backend.core.permissions import require_permission, Permission
    checker = require_permission(Permission.FINANCIAL_WRITE)
    # Admin has FINANCIAL_WRITE
    admin_user = models.User(role="admin")
    assert checker(admin_user) == admin_user

    # Receptionist lacks FINANCIAL_WRITE -> 403
    receptionist_user = models.User(role="receptionist")
    with pytest.raises(HTTPException) as exc:
        checker(receptionist_user)
    assert exc.value.status_code == 403
