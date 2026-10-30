"""
Tests for Phase G13 / Slice S31: Multi-Visit Endo Material Scenario & Legacy Invariance
(closes Phase G13).

Covers:
- G13-M11: a 2-session RCT work item deducts irrigants/files in session 1 and
  gutta-percha/sealer in session 2, with exact per-session stock deduction and exact
  work-item material cost aggregation.
- G13-M10 (runtime half): a pre-existing legacy ``TreatmentMaterialUsage`` row
  (``treatment_id`` set, ``care_session_id`` NULL) is left untouched by native
  care-session deductions and never leaks into the work-item cost aggregate.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

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


async def enable_native_writes(db, tenant_id: int):
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
        db, tenant_id, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True
    )


# name -> (price, starting qty, batch cost per unit)
ENDO_MATERIALS = {
    "irrigant": ("5.00", 20.0, "2.500000"),
    "file": ("12.00", 10.0, "6.000000"),
    "gp": ("8.00", 30.0, "4.000000"),
    "sealer": ("20.00", 5.0, "9.500000"),
}


@pytest.fixture
async def seed(async_db_session):
    db = async_db_session
    tenant = models.Tenant(name="S31 Endo Clinic", domain="s31.example.com", is_active=True)
    db.add(tenant)
    await db.flush()

    doctor = models.User(
        tenant_id=tenant.id, username="s31_doc", email="s31doc@a.com",
        hashed_password="x", role="doctor", is_active=True,
    )
    db.add(doctor)
    await db.flush()

    patient = models.Patient(
        tenant_id=tenant.id, name="S31 Patient", age=40, phone="+10000000031",
        medical_history="", notes="", assigned_doctor_id=doctor.id, is_deleted=False,
    )
    db.add(patient)
    await db.flush()

    rct = models.ClinicalWorkItem(
        tenant_id=tenant.id, patient_id=patient.id, kind="procedure",
        code="ENDO_RCT", status="active", created_by_user_id=doctor.id,
    )
    db.add(rct)

    warehouse = inv.Warehouse(tenant_id=tenant.id, name="Clinic WH", type="CLINIC")
    db.add(warehouse)
    await db.flush()

    materials, stock = {}, {}
    for key, (price, qty, cost) in ENDO_MATERIALS.items():
        mat = inv.Material(
            tenant_id=tenant.id, name=f"S31 {key}", type="NON_DIVISIBLE",
            base_unit="unit", standard_price=Decimal(price), packaging_ratio=1.0,
        )
        db.add(mat)
        await db.flush()
        batch = inv.Batch(
            material_id=mat.id, tenant_id=tenant.id, batch_number=f"S31-{key}",
            expiry_date=date.today() + timedelta(days=365),
            cost_per_unit=Decimal(cost),
        )
        db.add(batch)
        await db.flush()
        item = inv.StockItem(
            warehouse_id=warehouse.id, batch_id=batch.id, tenant_id=tenant.id, quantity=qty
        )
        db.add(item)
        await db.flush()
        materials[key], stock[key] = mat, item

    # Legacy (pre-S26-style) usage: bound to a Treatment, no care session / work item.
    legacy_treatment = models.Treatment(
        tenant_id=tenant.id, patient_id=patient.id, doctor_id=doctor.id,
        procedure="Legacy RCT", cost=Decimal("800.00"), status="Completed",
    )
    db.add(legacy_treatment)
    await db.flush()
    legacy_usage = inv.TreatmentMaterialUsage(
        tenant_id=tenant.id, treatment_id=legacy_treatment.id,
        care_session_id=None, work_item_id=None,
        material_id=materials["gp"].id, weight_score=1.0,
        quantity_used=2.0, cost_calculated=Decimal("8.000000"),
    )
    db.add(legacy_usage)
    await db.commit()
    await db.refresh(legacy_usage)

    return {
        "tenant": tenant, "doctor": doctor, "patient": patient, "rct": rct,
        "materials": materials, "stock": stock, "legacy_usage": legacy_usage,
    }


async def _qty(db, stock_item) -> float:
    return (
        await db.execute(select(inv.StockItem.quantity).where(inv.StockItem.id == stock_item.id))
    ).scalar_one()


def _start_session(client, headers, patient_id):
    r = client.post(f"/api/v1/patients/{patient_id}/care-sessions", headers=headers, json={})
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def _record(client, headers, patient_id, session_id, items, work_item_id):
    return client.post(
        f"/api/v1/patients/{patient_id}/care-sessions/{session_id}/material-usages",
        headers=headers,
        json={"items": items, "work_item_id": work_item_id},
    )


@pytest.mark.asyncio
async def test_g13_m11_two_session_rct_materials_and_exact_cost(client, seed, async_db_session):
    """G13-M11: S1 irrigant + files; S2 gutta-percha + sealer; exact cost aggregation."""
    await enable_native_writes(async_db_session, seed["tenant"].id)
    headers = make_headers(seed["doctor"])
    pid, wid = seed["patient"].id, seed["rct"].id
    mats, stock = seed["materials"], seed["stock"]

    # Session 1: cleaning & shaping -> irrigant + files.
    s1 = _start_session(client, headers, pid)
    r1 = _record(
        client, headers, pid, s1,
        [
            {"material_id": mats["irrigant"].id, "quantity": 6},
            {"material_id": mats["file"].id, "quantity": 3},
        ],
        wid,
    )
    assert r1.status_code == 201, r1.text
    assert len(r1.json()["data"]) == 2
    assert client.post(
        f"/api/v1/patients/{pid}/care-sessions/{s1}/finish", headers=headers, json={}
    ).status_code == 200

    # Session 1 only deducts session-1 materials.
    assert await _qty(async_db_session, stock["irrigant"]) == 14.0
    assert await _qty(async_db_session, stock["file"]) == 7.0
    assert await _qty(async_db_session, stock["gp"]) == 30.0
    assert await _qty(async_db_session, stock["sealer"]) == 5.0

    mid = client.get(
        f"/api/v1/patients/{pid}/clinical-work-items/{wid}/material-cost", headers=headers
    ).json()["data"]
    assert mid["total_cost"] == 33.0  # 6*2.50 + 3*6.00
    assert mid["usage_count"] == 2

    # Session 2: obturation -> gutta-percha + sealer.
    s2 = _start_session(client, headers, pid)
    r2 = _record(
        client, headers, pid, s2,
        [
            {"material_id": mats["gp"].id, "quantity": 4},
            {"material_id": mats["sealer"].id, "quantity": 1},
        ],
        wid,
    )
    assert r2.status_code == 201, r2.text
    assert client.post(
        f"/api/v1/patients/{pid}/care-sessions/{s2}/finish", headers=headers, json={}
    ).status_code == 200

    assert await _qty(async_db_session, stock["irrigant"]) == 14.0
    assert await _qty(async_db_session, stock["file"]) == 7.0
    assert await _qty(async_db_session, stock["gp"]) == 26.0
    assert await _qty(async_db_session, stock["sealer"]) == 4.0

    resp = client.get(
        f"/api/v1/patients/{pid}/clinical-work-items/{wid}/material-cost", headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["work_item_id"] == wid
    assert data["usage_count"] == 4
    assert data["pending_cost_count"] == 0
    # S1: 6*2.50 + 3*6.00 = 33.00 ; S2: 4*4.00 + 1*9.50 = 25.50
    assert data["total_cost"] == 58.5

    by_session = {s["care_session_id"]: s for s in data["sessions"]}
    assert set(by_session) == {s1, s2}
    assert by_session[s1]["cost"] == 33.0
    assert by_session[s2]["cost"] == 25.5
    assert {u["material_name"] for u in by_session[s1]["usages"]} == {"S31 irrigant", "S31 file"}
    assert {u["material_name"] for u in by_session[s2]["usages"]} == {"S31 gp", "S31 sealer"}

    # Native usages never create legacy Treatment rows and always link session + work item.
    native = (
        await async_db_session.execute(
            select(inv.TreatmentMaterialUsage).where(
                inv.TreatmentMaterialUsage.work_item_id == wid
            )
        )
    ).scalars().all()
    assert len(native) == 4
    assert all(u.treatment_id is None and u.care_session_id in {s1, s2} for u in native)


@pytest.mark.asyncio
async def test_g13_m10_legacy_usage_untouched_and_excluded_from_work_item_cost(
    client, seed, async_db_session
):
    """G13-M10 (runtime): native deductions leave legacy usage rows identical."""
    await enable_native_writes(async_db_session, seed["tenant"].id)
    headers = make_headers(seed["doctor"])
    pid, wid = seed["patient"].id, seed["rct"].id
    legacy = seed["legacy_usage"]
    before = (
        legacy.id, legacy.treatment_id, legacy.care_session_id, legacy.work_item_id,
        legacy.material_id, legacy.quantity_used, Decimal(str(legacy.cost_calculated)),
    )

    sid = _start_session(client, headers, pid)
    assert _record(
        client, headers, pid, sid,
        [{"material_id": seed["materials"]["gp"].id, "quantity": 5}],
        wid,
    ).status_code == 201

    await async_db_session.refresh(legacy)
    after = (
        legacy.id, legacy.treatment_id, legacy.care_session_id, legacy.work_item_id,
        legacy.material_id, legacy.quantity_used, Decimal(str(legacy.cost_calculated)),
    )
    assert after == before
    assert after[2] is None and after[3] is None

    data = client.get(
        f"/api/v1/patients/{pid}/clinical-work-items/{wid}/material-cost", headers=headers
    ).json()["data"]
    assert data["usage_count"] == 1
    assert data["total_cost"] == 20.0  # 5*4.00 only; legacy 8.00 row excluded
