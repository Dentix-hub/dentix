"""Regression tests for demo clinic hotfix bugs."""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest

from backend import models
from backend.clinical.lab_links import matching_procedure
from backend.clinical.legacy_mapping import (
    VerifiedPatientContext,
    map_legacy_treatment,
)
from backend.models.clinical import Treatment
from backend.schemas.inventory import BatchBase
from backend.services.inventory_service import InventoryService
from backend.services.material_resolution_service import MaterialResolutionService


@pytest.mark.parametrize("raw_status", ["In-Chair", "in-chair", "in chair", "in_chair"])
def test_appointment_accepts_in_chair_status_across_endpoints(
    client, test_patient, admin_headers, raw_status
):
    """Bug 2: Changing or creating appointments with In-Chair status must not 422 and normalizes to 'In-Chair'."""
    create_res = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": test_patient.id,
            "date_time": "2026-12-02T10:00:00",
            "status": raw_status,
        },
        headers=admin_headers,
    )
    assert create_res.status_code == 201, create_res.text
    appt_id = create_res.json()["data"]["id"]
    assert create_res.json()["data"]["status"] == "In-Chair"

    put_res = client.put(
        f"/api/v1/appointments/{appt_id}",
        json={"status": raw_status},
        headers=admin_headers,
    )
    assert put_res.status_code == 200, put_res.text
    assert put_res.json()["data"]["status"] == "In-Chair"

    status_res = client.put(
        f"/api/v1/appointments/{appt_id}/status",
        params={"status": raw_status},
        headers=admin_headers,
    )
    assert status_res.status_code == 200, status_res.text
    assert status_res.json()["data"]["status"] == "In-Chair"


def test_matching_procedure_supports_bridge_and_denture_aliases():
    assert matching_procedure("جسر ثابت – Fixed Bridge", "Bridge")
    assert matching_procedure("جسر ثابت – Fixed Bridge", "جسر ثابت – Fixed Bridge")
    assert matching_procedure("تاج زيركون – Zirconia Crown", "Crown")
    assert matching_procedure("طقم جزئي أكريليك – Partial Acrylic Denture", "Partial Denture")
    assert not matching_procedure("Composite Filling", "Bridge")


@pytest.mark.parametrize(
    "treatment_proc,work_type",
    [
        ("جسر ثابت – Fixed Bridge", "Bridge"),
        ("تاج زيركون – Zirconia Crown", "تاج زيركون – Zirconia Crown"),
        ("تاج زيركون – Zirconia Crown", "Crown"),
        ("طقم جزئي أكريليك – Partial Acrylic Denture", "Partial Denture"),
    ],
)
def test_create_lab_order_linked_to_treatment_accepts_matching_work_type(
    client, db_session, test_user, test_patient, admin_headers, treatment_proc, work_type
):
    """Bug 3: Linked lab orders accept bilingual treatment names and UI dropdown work_type values."""
    lab = models.Laboratory(name="Demo Ceramics Lab", tenant_id=test_user.tenant_id)
    treatment = models.Treatment(
        patient_id=test_patient.id,
        tooth_number=16,
        procedure=treatment_proc,
        diagnosis="Caries",
        cost=Decimal("2500.00"),
        discount=Decimal("0.00"),
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    db_session.add_all([lab, treatment])
    db_session.commit()
    db_session.refresh(lab)
    db_session.refresh(treatment)

    res = client.post(
        "/api/v1/lab-orders",
        json={
            "patient_id": test_patient.id,
            "laboratory_id": lab.id,
            "treatment_id": treatment.id,
            "work_type": work_type,
            "tooth_number": "16",
            "cost": 600,
            "paid_now": 0,
            "price_to_patient": 0,
        },
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["treatment_id"] == treatment.id
    assert body["work_type"] == work_type


def test_create_lab_order_linked_to_treatment_still_rejects_mismatched_work_type(
    client, db_session, test_user, test_patient, admin_headers
):
    lab = models.Laboratory(name="Demo Lab", tenant_id=test_user.tenant_id)
    treatment = models.Treatment(
        patient_id=test_patient.id,
        tooth_number=14,
        procedure="Composite Filling",
        diagnosis="Caries",
        cost=Decimal("500.00"),
        discount=Decimal("0.00"),
        tenant_id=test_user.tenant_id,
        doctor_id=test_user.id,
    )
    db_session.add_all([lab, treatment])
    db_session.commit()
    db_session.refresh(lab)
    db_session.refresh(treatment)

    res = client.post(
        "/api/v1/lab-orders",
        json={
            "patient_id": test_patient.id,
            "laboratory_id": lab.id,
            "treatment_id": treatment.id,
            "work_type": "Bridge",
            "tooth_number": "14",
        },
        headers=admin_headers,
    )
    assert res.status_code == 422
    assert "لا يطابق العلاج" in res.json()["detail"]


@pytest.mark.asyncio
async def test_add_stock_preserves_existing_standard_price_and_backfills_zero(
    async_db_session,
):
    """Bug 7: Receiving stock at pack price 500 must not overwrite an existing standard_price of 250."""
    tenant = models.Tenant(name="Inventory Price Clinic")
    async_db_session.add(tenant)
    await async_db_session.flush()

    user = models.User(
        username="inv_admin",
        hashed_password="x",
        role="admin",
        tenant_id=tenant.id,
        is_active=True,
    )
    wh = models.Warehouse(name="Clinic", type="CLINIC", tenant_id=tenant.id)
    configured_mat = models.Material(
        name="Composite Pack",
        base_unit="g",
        type="DIVISIBLE",
        packaging_ratio=5.0,
        standard_price=Decimal("250.00"),
        tenant_id=tenant.id,
    )
    unconfigured_mat = models.Material(
        name="Etch Gel",
        base_unit="ml",
        type="DIVISIBLE",
        packaging_ratio=2.0,
        standard_price=Decimal("0.00"),
        tenant_id=tenant.id,
    )
    async_db_session.add_all([user, wh, configured_mat, unconfigured_mat])
    await async_db_session.commit()

    service = InventoryService(async_db_session)
    await service.add_stock(
        material_id=configured_mat.id,
        warehouse_id=wh.id,
        quantity=2,
        batch_data=BatchBase(
            batch_number="EXP-20270531-5930",
            expiry_date=date(2027, 5, 31),
            cost_per_unit=Decimal("100.00"),  # 100 * 5 = 500 pack price
        ),
        user_id=user.id,
        tenant_id=tenant.id,
    )
    await service.add_stock(
        material_id=unconfigured_mat.id,
        warehouse_id=wh.id,
        quantity=1,
        batch_data=BatchBase(
            batch_number="EXP-20270630-1111",
            expiry_date=date(2027, 6, 30),
            cost_per_unit=Decimal("40.00"),  # 40 * 2 = 80 pack price
        ),
        user_id=user.id,
        tenant_id=tenant.id,
    )

    await async_db_session.refresh(configured_mat)
    await async_db_session.refresh(unconfigured_mat)
    assert configured_mat.standard_price == Decimal("250.00")
    assert unconfigured_mat.standard_price == Decimal("80.00")


@pytest.mark.asyncio
async def test_material_resolution_includes_direct_material_weights_and_isolates_tenant(
    async_db_session,
):
    """Bug 8: MaterialResolutionService resolves direct material_id rules (category_id=None) scoped by tenant."""
    tenant_a = models.Tenant(name="Clinic A")
    tenant_b = models.Tenant(name="Clinic B")
    async_db_session.add_all([tenant_a, tenant_b])
    await async_db_session.flush()

    cat = models.MaterialCategory(
        name_en="Restorative", name_ar="حشوات", default_unit="g", default_type="DIVISIBLE"
    )
    async_db_session.add(cat)
    await async_db_session.flush()

    mat_a = models.Material(
        name="Composite A",
        base_unit="g",
        type="NON_DIVISIBLE",
        packaging_ratio=1.0,
        category_id=cat.id,
        tenant_id=tenant_a.id,
    )
    mat_deleted = models.Material(
        name="Deleted Mat",
        base_unit="g",
        type="NON_DIVISIBLE",
        packaging_ratio=1.0,
        category_id=cat.id,
        tenant_id=tenant_a.id,
        is_deleted=True,
    )
    mat_other_tenant = models.Material(
        name="Tenant B Composite",
        base_unit="g",
        type="NON_DIVISIBLE",
        packaging_ratio=1.0,
        category_id=cat.id,
        tenant_id=tenant_b.id,
    )
    proc = models.Procedure(name="Filling", price=400.0, tenant_id=tenant_a.id)
    async_db_session.add_all([mat_a, mat_deleted, mat_other_tenant, proc])
    await async_db_session.flush()

    async_db_session.add_all([
        models.ProcedureMaterialWeight(
            procedure_id=proc.id,
            category_id=None,
            material_id=mat_a.id,
            weight=2.0,
            tenant_id=tenant_a.id,
        ),
        models.ProcedureMaterialWeight(
            procedure_id=proc.id,
            category_id=None,
            material_id=mat_deleted.id,
            weight=1.0,
            tenant_id=tenant_a.id,
        ),
        models.ProcedureMaterialWeight(
            procedure_id=proc.id,
            category_id=None,
            material_id=mat_other_tenant.id,
            weight=1.0,
            tenant_id=tenant_a.id,
        ),
    ])
    await async_db_session.commit()

    resolver = MaterialResolutionService(async_db_session)
    suggestions = await resolver.resolve_materials_for_procedure(proc.id, tenant_a.id)
    assert [s["material_id"] for s in suggestions] == [mat_a.id]
    assert suggestions[0]["weight"] == 2.0
    assert suggestions[0]["category_id"] == cat.id


@pytest.mark.asyncio
async def test_consume_stock_falls_back_to_main_warehouse_when_clinic_empty(
    async_db_session,
):
    """Bug 8: consume_stock prefers CLINIC warehouse when warehouse_id=None, but falls back to MAIN warehouse."""
    tenant_a = models.Tenant(name="WH Clinic A")
    tenant_b = models.Tenant(name="WH Clinic B")
    async_db_session.add_all([tenant_a, tenant_b])
    await async_db_session.flush()

    user_a = models.User(
        username="wh_user_a", hashed_password="x", role="admin", tenant_id=tenant_a.id, is_active=True
    )
    clinic_wh = models.Warehouse(name="Clinic", type="CLINIC", tenant_id=tenant_a.id)
    main_wh = models.Warehouse(name="Main", type="MAIN", tenant_id=tenant_a.id)
    other_wh = models.Warehouse(name="Other", type="MAIN", tenant_id=tenant_b.id)
    mat_a = models.Material(
        name="Carpule", base_unit="unit", type="NON_DIVISIBLE", packaging_ratio=1.0, tenant_id=tenant_a.id
    )
    async_db_session.add_all([user_a, clinic_wh, main_wh, other_wh, mat_a])
    await async_db_session.flush()

    batch_a = models.Batch(
        material_id=mat_a.id, batch_number="B-MAIN", expiry_date=date(2028, 1, 1), tenant_id=tenant_a.id
    )
    batch_b = models.Batch(
        material_id=mat_a.id, batch_number="B-OTHER", expiry_date=date(2027, 1, 1), tenant_id=tenant_b.id
    )
    async_db_session.add_all([batch_a, batch_b])
    await async_db_session.flush()

    stock_a = models.StockItem(warehouse_id=main_wh.id, batch_id=batch_a.id, quantity=5.0, tenant_id=tenant_a.id)
    stock_b = models.StockItem(warehouse_id=other_wh.id, batch_id=batch_b.id, quantity=5.0, tenant_id=tenant_b.id)
    async_db_session.add_all([stock_a, stock_b])
    await async_db_session.commit()

    service = InventoryService(async_db_session)
    movements = await service.consume_stock(
        material_id=mat_a.id,
        quantity=1.0,
        tenant_id=tenant_a.id,
        user_id=user_a.id,
        db=async_db_session,
        commit=False,
    )
    await async_db_session.flush()
    await async_db_session.refresh(stock_a)
    await async_db_session.refresh(stock_b)
    assert len(movements) == 1
    assert stock_a.quantity == 4.0
    assert stock_b.quantity == 5.0


def test_standalone_lab_treatment_does_not_emit_legacy_review_warning():
    """Bug 20: Standalone lab billing rows ('عمل معمل: ...' + Link:LabOrder:N) must not trigger UNKNOWN_PROCEDURE_CODE."""
    ctx = VerifiedPatientContext(patient_id=398, tenant_id=1)
    crown_row = Treatment(
        id=1,
        patient_id=398,
        tenant_id=1,
        tooth_number=26,
        procedure="عمل معمل: تاج زيركون",
        status="Done",
        cost=Decimal("1500.00"),
        discount=Decimal("0.00"),
        notes="Link:LabOrder:17",
        date=datetime(2026, 11, 28, tzinfo=timezone.utc),
    )
    wi_crown, _, crown_issues = map_legacy_treatment(crown_row, ctx)
    assert not any(iss.code == "UNKNOWN_PROCEDURE_CODE" for iss in crown_issues)
    assert wi_crown is not None
    assert wi_crown.code == "PROS_CROWN"
    assert wi_crown.notes == "Link:LabOrder:17"

    guard_row = Treatment(
        id=2,
        patient_id=398,
        tenant_id=1,
        tooth_number=None,
        procedure="عمل معمل: Night Guard - Acrylic",
        status="Done",
        cost=Decimal("900.00"),
        discount=Decimal("0.00"),
        notes="Link:LabOrder:18",
        date=datetime(2026, 11, 28, tzinfo=timezone.utc),
    )
    _, _, guard_issues = map_legacy_treatment(guard_row, ctx)
    assert not guard_issues
