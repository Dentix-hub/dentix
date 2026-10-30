"""
Tests for Phase G13 / Slice S30: Point-of-Care Material Suggestion, Session Deduction
& Cost Aggregation.

Covers:
- G13-M04: read-only material suggestion by canonical procedure code
- G13-M05: no stock deduction / usage rows until actual use (suggestion, proposed work items)
- G13-M06: deduct at actual use point via care session, TreatmentMaterialUsage linkage
- G13-M07: different materials per session of the same work item
- G13-M08: divisible-material logic preserved (CONFIRM_OPEN_REQUIRED, open package virtual use)
- G13-M09: aggregated work-item material cost across sessions
- Fail-closed feature flag, tenant isolation, RBAC, atomic (no partial) deduction
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from backend import models
from backend.auth import create_access_token
from backend.models import inventory as inv
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService


def make_headers(user: models.User) -> dict:
    token = create_access_token(
        data={"sub": user.username, "tenant_id": user.tenant_id, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


async def set_native_writes_flag(db, tenant_id: int, enabled: bool):
    flag = (
        await db.execute(
            select(models.FeatureFlag).where(
                models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES
            )
        )
    ).scalar_one_or_none()
    if not flag:
        flag = models.FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            description="Clinical native writes",
            is_global_enabled=True,
            rollout_percentage=0,
        )
        db.add(flag)
        await db.commit()
        await db.refresh(flag)
    await FeatureFlagService.set_tenant_override(
        db, tenant_id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, enabled
    )


def _material(tenant_id, name, mtype, price="10.00"):
    return inv.Material(
        tenant_id=tenant_id,
        name=name,
        type=mtype,
        base_unit="unit" if mtype == "NON_DIVISIBLE" else "g",
        standard_price=Decimal(price),
        packaging_ratio=1.0,
    )


@pytest.fixture
async def seed(async_db_session):
    db = async_db_session
    t1 = models.Tenant(name="S30 Alpha", domain="s30a.example.com", is_active=True)
    t2 = models.Tenant(name="S30 Beta", domain="s30b.example.com", is_active=True)
    db.add_all([t1, t2])
    await db.flush()

    doctor = models.User(
        tenant_id=t1.id, username="s30_doc", email="s30doc@a.com",
        hashed_password="x", role="doctor", is_active=True,
    )
    receptionist = models.User(
        tenant_id=t1.id, username="s30_recep", email="s30recep@a.com",
        hashed_password="x", role="receptionist", is_active=True,
    )
    other_doctor = models.User(
        tenant_id=t2.id, username="s30_doc_b", email="s30docb@b.com",
        hashed_password="x", role="doctor", is_active=True,
    )
    db.add_all([doctor, receptionist, other_doctor])
    await db.flush()

    patient = models.Patient(
        tenant_id=t1.id, name="S30 Patient", age=30, phone="+10000000030",
        medical_history="", notes="", assigned_doctor_id=doctor.id, is_deleted=False,
    )
    db.add(patient)
    await db.flush()

    work_item = models.ClinicalWorkItem(
        tenant_id=t1.id, patient_id=patient.id, kind="procedure",
        code="REST_COMPOSITE", status="active", created_by_user_id=doctor.id,
    )
    proposed_item = models.ClinicalWorkItem(
        tenant_id=t1.id, patient_id=patient.id, kind="procedure",
        code="REST_COMPOSITE", status="proposed", created_by_user_id=doctor.id,
    )
    cancelled_item = models.ClinicalWorkItem(
        tenant_id=t1.id, patient_id=patient.id, kind="procedure",
        code="REST_COMPOSITE", status="cancelled", created_by_user_id=doctor.id,
    )
    db.add_all([work_item, proposed_item, cancelled_item])

    warehouse = inv.Warehouse(tenant_id=t1.id, name="Clinic WH", type="CLINIC")
    db.add(warehouse)
    await db.flush()

    irrigant = _material(t1.id, "Irrigant NaOCl", "NON_DIVISIBLE", "5.00")
    gp = _material(t1.id, "Gutta Percha", "NON_DIVISIBLE", "8.00")
    composite = _material(t1.id, "Composite A2", "DIVISIBLE", "150.00")
    db.add_all([irrigant, gp, composite])
    await db.flush()

    stock = {}
    for key, mat, qty, cost in (
        ("irrigant", irrigant, 10.0, "2.500000"),
        ("gp", gp, 10.0, "4.000000"),
        ("composite", composite, 0.0, "100.000000"),
    ):
        batch = inv.Batch(
            material_id=mat.id, tenant_id=t1.id, batch_number=f"B-{key}",
            expiry_date=date.today() + timedelta(days=365),
            cost_per_unit=Decimal(cost),
        )
        db.add(batch)
        await db.flush()
        item = inv.StockItem(
            warehouse_id=warehouse.id, batch_id=batch.id, tenant_id=t1.id, quantity=qty
        )
        db.add(item)
        await db.flush()
        stock[key] = item

    procedure = models.Procedure(name="Composite Filling", price=Decimal("500.00"), tenant_id=t1.id)
    db.add(procedure)
    await db.flush()
    db.add(
        inv.ProcedureMaterialWeight(
            procedure_id=procedure.id, material_id=irrigant.id, tenant_id=t1.id, weight=2.0
        )
    )
    await db.commit()

    return {
        "t1": t1, "t2": t2, "doctor": doctor, "receptionist": receptionist,
        "other_doctor": other_doctor, "patient": patient, "work_item": work_item,
        "proposed_item": proposed_item, "cancelled_item": cancelled_item,
        "irrigant": irrigant, "gp": gp, "composite": composite,
        "stock": stock, "procedure": procedure,
    }


async def _qty(db, stock_item) -> float:
    return (
        await db.execute(select(inv.StockItem.quantity).where(inv.StockItem.id == stock_item.id))
    ).scalar_one()


async def _count(db, model) -> int:
    return (await db.execute(select(func.count(model.id)))).scalar_one()


def _start_session(client, headers, patient_id):
    r = client.post(f"/api/v1/patients/{patient_id}/care-sessions", headers=headers, json={})
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def _record(client, headers, patient_id, session_id, items, work_item_id=None):
    body = {"items": items}
    if work_item_id is not None:
        body["work_item_id"] = work_item_id
    return client.post(
        f"/api/v1/patients/{patient_id}/care-sessions/{session_id}/material-usages",
        headers=headers,
        json=body,
    )


@pytest.mark.asyncio
async def test_flag_off_returns_404_on_all_endpoints(client, seed, async_db_session):
    await set_native_writes_flag(async_db_session, seed["t1"].id, False)
    headers = make_headers(seed["doctor"])
    pid, wid = seed["patient"].id, seed["work_item"].id

    assert client.get(
        f"/api/v1/patients/{pid}/clinical-work-items/{wid}/material-suggestions", headers=headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/patients/{pid}/clinical-work-items/{wid}/material-cost", headers=headers
    ).status_code == 404
    assert _record(client, headers, pid, 1, [{"material_id": 1, "quantity": 1}]).status_code == 404


@pytest.mark.asyncio
async def test_suggestion_is_read_only_and_proposed_item_deducts_nothing(
    client, seed, async_db_session
):
    """G13-M04 + G13-M05."""
    await set_native_writes_flag(async_db_session, seed["t1"].id, True)
    headers = make_headers(seed["doctor"])
    moves_before = await _count(async_db_session, inv.StockMovement)
    usages_before = await _count(async_db_session, inv.TreatmentMaterialUsage)
    qty_before = await _qty(async_db_session, seed["stock"]["irrigant"])

    resp = client.get(
        f"/api/v1/patients/{seed['patient'].id}/clinical-work-items/"
        f"{seed['proposed_item'].id}/material-suggestions?step_code=IRRIGATION",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["procedure_code"] == "REST_COMPOSITE"
    assert data["step_code"] == "IRRIGATION"
    assert data["procedure_ids"] == [seed["procedure"].id]
    assert [s["material_id"] for s in data["suggestions"]] == [seed["irrigant"].id]

    assert await _count(async_db_session, inv.StockMovement) == moves_before
    assert await _count(async_db_session, inv.TreatmentMaterialUsage) == usages_before
    assert await _qty(async_db_session, seed["stock"]["irrigant"]) == qty_before


@pytest.mark.asyncio
async def test_record_usage_deducts_at_use_and_links_session_and_work_item(
    client, seed, async_db_session
):
    """G13-M06: stock deducted once, usage linked, no legacy Treatment created."""
    await set_native_writes_flag(async_db_session, seed["t1"].id, True)
    headers = make_headers(seed["doctor"])
    pid, wid = seed["patient"].id, seed["work_item"].id
    sid = _start_session(client, headers, pid)
    treatments_before = await _count(async_db_session, models.Treatment)

    resp = _record(
        client, headers, pid, sid, [{"material_id": seed["irrigant"].id, "quantity": 3}], wid
    )
    assert resp.status_code == 201, resp.text
    rows = resp.json()["data"]
    assert len(rows) == 1
    assert rows[0]["care_session_id"] == sid
    assert rows[0]["work_item_id"] == wid
    assert rows[0]["quantity_used"] == 3
    assert rows[0]["cost_calculated"] == 7.5  # 3 * 2.50 batch cost
    assert rows[0]["material_name"] == "Irrigant NaOCl"

    assert await _qty(async_db_session, seed["stock"]["irrigant"]) == 7.0
    ref = (
        await async_db_session.execute(
            select(inv.StockMovement).where(inv.StockMovement.reference_id == f"CARE_SESSION:{sid}")
        )
    ).scalars().all()
    assert len(ref) == 1 and ref[0].change_amount == -3.0

    tmu = (
        await async_db_session.execute(
            select(inv.TreatmentMaterialUsage).where(
                inv.TreatmentMaterialUsage.care_session_id == sid
            )
        )
    ).scalars().all()
    assert len(tmu) == 1 and tmu[0].treatment_id is None and tmu[0].work_item_id == wid
    assert await _count(async_db_session, models.Treatment) == treatments_before

    event = (
        await async_db_session.execute(
            select(models.ClinicalEvent).where(
                models.ClinicalEvent.care_session_id == sid,
                models.ClinicalEvent.event_type == "care_session_materials_recorded",
            )
        )
    ).scalars().all()
    assert len(event) == 1


@pytest.mark.asyncio
async def test_insufficient_stock_is_400_with_no_partial_deduction(
    client, seed, async_db_session
):
    await set_native_writes_flag(async_db_session, seed["t1"].id, True)
    headers = make_headers(seed["doctor"])
    pid = seed["patient"].id
    sid = _start_session(client, headers, pid)

    resp = _record(
        client, headers, pid, sid,
        [
            {"material_id": seed["irrigant"].id, "quantity": 2},
            {"material_id": seed["gp"].id, "quantity": 999},
        ],
    )
    assert resp.status_code == 400, resp.text
    assert await _qty(async_db_session, seed["stock"]["irrigant"]) == 10.0
    assert await _qty(async_db_session, seed["stock"]["gp"]) == 10.0
    assert await _count(async_db_session, inv.TreatmentMaterialUsage) == 0


@pytest.mark.asyncio
async def test_divisible_without_open_package_is_409_and_rolls_back_earlier_items(
    client, seed, async_db_session
):
    """G13-M08: CONFIRM_OPEN_REQUIRED preserved; earlier deductions in the call rolled back."""
    await set_native_writes_flag(async_db_session, seed["t1"].id, True)
    headers = make_headers(seed["doctor"])
    pid = seed["patient"].id
    sid = _start_session(client, headers, pid)

    # Give composite one unopened package so validate_stock passes but consume demands opening.
    seed["stock"]["composite"].quantity = 5.0
    await async_db_session.commit()

    resp = _record(
        client, headers, pid, sid,
        [
            {"material_id": seed["irrigant"].id, "quantity": 2},
            {"material_id": seed["composite"].id, "quantity": 1},
        ],
    )
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "CONFIRM_OPEN_REQUIRED"
    assert await _qty(async_db_session, seed["stock"]["irrigant"]) == 10.0
    assert await _count(async_db_session, inv.TreatmentMaterialUsage) == 0


@pytest.mark.asyncio
async def test_divisible_with_open_package_records_pending_cost(
    client, seed, async_db_session
):
    """G13-M08: open package is consumed virtually; cost stays NULL until package close."""
    await set_native_writes_flag(async_db_session, seed["t1"].id, True)
    headers = make_headers(seed["doctor"])
    pid, wid = seed["patient"].id, seed["work_item"].id
    sid = _start_session(client, headers, pid)

    package = inv.MaterialSession(
        tenant_id=seed["t1"].id,
        stock_item_id=seed["stock"]["composite"].id,
        opened_at=datetime.now(timezone.utc),
        status="ACTIVE",
        remaining_est=1.0,
        doctor_id=seed["doctor"].id,
        patient_id=pid,
    )
    async_db_session.add(package)
    await async_db_session.commit()
    await async_db_session.refresh(package)

    resp = _record(
        client, headers, pid, sid, [{"material_id": seed["composite"].id, "quantity": 0.5}], wid
    )
    assert resp.status_code == 201, resp.text
    row = resp.json()["data"][0]
    assert row["session_id"] == package.id
    assert row["quantity_used"] is None
    assert row["cost_calculated"] is None

    cost = client.get(
        f"/api/v1/patients/{pid}/clinical-work-items/{wid}/material-cost", headers=headers
    ).json()["data"]
    assert cost["pending_cost_count"] == 1
    assert cost["total_cost"] == 0.0


@pytest.mark.asyncio
async def test_different_materials_per_session_and_work_item_cost_aggregation(
    client, seed, async_db_session
):
    """G13-M07 + G13-M09: session 1 irrigant, session 2 gutta-percha; totals aggregate."""
    await set_native_writes_flag(async_db_session, seed["t1"].id, True)
    headers = make_headers(seed["doctor"])
    pid, wid = seed["patient"].id, seed["work_item"].id

    s1 = _start_session(client, headers, pid)
    assert _record(
        client, headers, pid, s1, [{"material_id": seed["irrigant"].id, "quantity": 4}], wid
    ).status_code == 201
    assert client.post(
        f"/api/v1/patients/{pid}/care-sessions/{s1}/finish", headers=headers, json={}
    ).status_code == 200

    s2 = _start_session(client, headers, pid)
    assert _record(
        client, headers, pid, s2, [{"material_id": seed["gp"].id, "quantity": 2}], wid
    ).status_code == 201

    resp = client.get(
        f"/api/v1/patients/{pid}/clinical-work-items/{wid}/material-cost", headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["work_item_id"] == wid
    assert data["usage_count"] == 2
    assert data["pending_cost_count"] == 0
    assert data["total_cost"] == 18.0  # 4*2.50 + 2*4.00
    by_session = {s["care_session_id"]: s for s in data["sessions"]}
    assert by_session[s1]["cost"] == 10.0
    assert by_session[s2]["cost"] == 8.0
    assert by_session[s1]["usages"][0]["material_name"] == "Irrigant NaOCl"
    assert by_session[s2]["usages"][0]["material_name"] == "Gutta Percha"


@pytest.mark.asyncio
async def test_terminal_session_and_cancelled_work_item_are_rejected(
    client, seed, async_db_session
):
    await set_native_writes_flag(async_db_session, seed["t1"].id, True)
    headers = make_headers(seed["doctor"])
    pid = seed["patient"].id
    item = [{"material_id": seed["irrigant"].id, "quantity": 1}]

    sid = _start_session(client, headers, pid)
    assert _record(
        client, headers, pid, sid, item, seed["cancelled_item"].id
    ).status_code == 400

    client.post(f"/api/v1/patients/{pid}/care-sessions/{sid}/finish", headers=headers, json={})
    assert _record(client, headers, pid, sid, item).status_code == 400
    assert await _qty(async_db_session, seed["stock"]["irrigant"]) == 10.0


@pytest.mark.asyncio
async def test_tenant_isolation_and_rbac(client, seed, async_db_session):
    await set_native_writes_flag(async_db_session, seed["t1"].id, True)
    await set_native_writes_flag(async_db_session, seed["t2"].id, True)
    doc_headers = make_headers(seed["doctor"])
    pid = seed["patient"].id
    sid = _start_session(client, doc_headers, pid)
    item = [{"material_id": seed["irrigant"].id, "quantity": 1}]

    # Other tenant cannot see/record against this patient's session.
    assert _record(client, make_headers(seed["other_doctor"]), pid, sid, item).status_code == 404
    # Receptionist lacks CLINICAL_WRITE.
    assert _record(client, make_headers(seed["receptionist"]), pid, sid, item).status_code == 403
    assert await _qty(async_db_session, seed["stock"]["irrigant"]) == 10.0
