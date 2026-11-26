"""Regression test suite for all backend/API findings in the QA report (QA-01..QA-25)."""

import base64
import io
import json
from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from backend import models
from backend.auth import get_password_hash
from backend.services.accounting_service import AccountingService
from backend.services.clinical_rollout_service import ClinicalRolloutService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.tenant_archive_embedded_refs import remap_event_payload


def _enable_native_writes(db_session, tenant_id: int) -> None:
    ff = db_session.query(models.FeatureFlag).filter_by(key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES).first()
    if not ff:
        ff = models.FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            description="Enable native writes",
            is_global_enabled=False,
            rollout_percentage=0,
        )
        db_session.add(ff)
        db_session.flush()
    tf = (
        db_session.query(models.TenantFeature)
        .filter_by(tenant_id=tenant_id, feature_key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES)
        .first()
    )
    if not tf:
        db_session.add(
            models.TenantFeature(
                tenant_id=tenant_id,
                feature_key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
                is_enabled=True,
            )
        )
    else:
        tf.is_enabled = True
    db_session.commit()


def test_qa01_native_writes_alone_projects_workspace_and_rollback_reverts(
    client, db_session, test_tenant, test_patient, auth_headers, super_admin_user
):
    _enable_native_writes(db_session, test_tenant.id)

    proc_res = client.post(
        f"/api/v1/patients/{test_patient.id}/clinical-procedures",
        json={"code": "ENDO_RCT", "targets": [{"target_kind": "tooth", "tooth_key": "26"}]},
        headers=auth_headers,
    )
    assert proc_res.status_code == 201, proc_res.text

    find_res = client.post(
        f"/api/v1/patients/{test_patient.id}/clinical-findings",
        json={"code": "CARIES", "targets": [{"target_kind": "tooth", "tooth_key": "16"}]},
        headers=auth_headers,
    )
    assert find_res.status_code == 201, find_res.text

    ws_res = client.get(
        f"/api/v1/patients/{test_patient.id}/clinical-workspace",
        headers=auth_headers,
    )
    assert ws_res.status_code == 200, ws_res.text
    snapshot = ws_res.json()["data"]
    assert snapshot["read_mode"] == "VNEXT_PRIMARY"
    assert any(wi["code"] == "ENDO_RCT" for wi in snapshot["work_items"])
    assert any(p["code"] == "ENDO_RCT" for p in snapshot["teeth"]["26"]["procedures"])
    assert any(f["code"] == "CARIES" for f in snapshot["teeth"]["16"]["findings"])


@pytest.mark.asyncio
async def test_qa01_rollback_still_resolves_legacy_only(async_db_session, test_tenant, super_admin_user):
    async_db_session.add(
        models.FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            description="Native writes",
            is_global_enabled=False,
            rollout_percentage=0,
        )
    )
    await async_db_session.flush()
    async_db_session.add(
        models.TenantFeature(
            tenant_id=test_tenant.id,
            feature_key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            is_enabled=True,
        )
    )
    await async_db_session.commit()

    rollout = ClinicalRolloutService(async_db_session)
    status_before = await rollout.get_rollout_status(test_tenant.id)
    assert status_before.rollout_mode == "VNEXT_PRIMARY"

    rb = await rollout.rollback_tenant(test_tenant.id, super_admin_user)
    assert rb.current_mode == "LEGACY_ONLY"


def test_qa05_qa22_resumable_and_next_visit_requests_no_missing_greenlet(
    client, db_session, test_tenant, test_patient, auth_headers
):
    _enable_native_writes(db_session, test_tenant.id)

    wi_res = client.post(
        f"/api/v1/patients/{test_patient.id}/clinical-procedures",
        json={"code": "ENDO_RCT", "targets": [{"target_kind": "tooth", "tooth_key": "46"}]},
        headers=auth_headers,
    )
    assert wi_res.status_code == 201, wi_res.text
    wi_id = wi_res.json()["data"]["id"]

    # Create paused session with template steps (containing work_item_id)
    s1_res = client.post(
        f"/api/v1/patients/{test_patient.id}/care-sessions",
        json={"work_item_ids": [wi_id], "notes": "Session 1"},
        headers=auth_headers,
    )
    assert s1_res.status_code == 201, s1_res.text
    s1_id = s1_res.json()["data"]["id"]
    step_res = client.post(
        f"/api/v1/patients/{test_patient.id}/care-sessions/{s1_id}/steps/from-template",
        json={"template_code": "ENDO_RCT", "work_item_id": wi_id},
        headers=auth_headers,
    )
    assert step_res.status_code == 201, step_res.text
    pause_res = client.post(
        f"/api/v1/patients/{test_patient.id}/care-sessions/{s1_id}/transition",
        json={"to_status": "paused"},
        headers=auth_headers,
    )
    assert pause_res.status_code == 200, pause_res.text

    # Create second active session with steps
    s2_res = client.post(
        f"/api/v1/patients/{test_patient.id}/care-sessions",
        json={"work_item_ids": [wi_id], "notes": "Session 2"},
        headers=auth_headers,
    )
    assert s2_res.status_code == 201, s2_res.text
    s2_id = s2_res.json()["data"]["id"]
    client.post(
        f"/api/v1/patients/{test_patient.id}/care-sessions/{s2_id}/steps/from-template",
        json={"template_code": "ENDO_RCT", "work_item_id": wi_id},
        headers=auth_headers,
    )

    # QA-05: fresh HTTP session resumable must return 200 with both active & paused summaries
    resumable = client.get(
        f"/api/v1/patients/{test_patient.id}/care-sessions/resumable",
        headers=auth_headers,
    )
    assert resumable.status_code == 200, resumable.text
    rdata = resumable.json()["data"]
    assert rdata["active_session"]["id"] == s2_id
    assert rdata["paused_session"]["id"] == s1_id

    # QA-22: POST and GET patient next-visit-requests must return 201/200 with patient_name populated
    nvr_post = client.post(
        f"/api/v1/patients/{test_patient.id}/next-visit-requests",
        json={"reason": "متابعة حشو عصب", "suggested_duration_minutes": 30},
        headers=auth_headers,
    )
    assert nvr_post.status_code == 201, nvr_post.text
    assert nvr_post.json()["data"]["patient_name"] == test_patient.name

    nvr_list = client.get(
        f"/api/v1/patients/{test_patient.id}/next-visit-requests",
        headers=auth_headers,
    )
    assert nvr_list.status_code == 200, nvr_list.text
    assert len(nvr_list.json()["data"]) == 1

    # Finishing session WITH next_visit_request must also return 200 without MissingGreenlet
    finish_res = client.post(
        f"/api/v1/patients/{test_patient.id}/care-sessions/{s2_id}/finish",
        json={
            "notes": "Completed visit",
            "next_visit_request": {
                "reason": "Obturation",
                "suggested_duration_minutes": 45,
            },
        },
        headers=auth_headers,
    )
    assert finish_res.status_code == 200, finish_res.text
    assert len(finish_res.json()["data"]["next_visit_requests"]) == 1


def test_qa07_patient_rejects_future_dob_negative_age_and_blank_name(client, admin_headers):
    future_dob = (date.today() + timedelta(days=365)).isoformat()
    r_dob = client.post(
        "/api/v1/patients",
        json={"name": "Future Patient", "date_of_birth": future_dob},
        headers=admin_headers,
    )
    assert r_dob.status_code == 422

    r_age = client.post(
        "/api/v1/patients",
        json={"name": "Negative Age", "age": -3},
        headers=admin_headers,
    )
    assert r_age.status_code == 422

    r_blank = client.post(
        "/api/v1/patients",
        json={"name": "   ", "age": 25},
        headers=admin_headers,
    )
    assert r_blank.status_code == 422

    r_ok = client.post(
        "/api/v1/patients",
        json={"name": "  Valid Patient  ", "age": 25},
        headers=admin_headers,
    )
    assert r_ok.status_code == 200, r_ok.text
    assert r_ok.json()["data"]["name"] == "Valid Patient"


def test_qa10_qa11_qa12_qa13_inventory_serialization_and_validation(client, admin_headers):
    cat_res = client.post(
        "/api/v1/inventory/categories",
        json={"name_en": "Endodontics", "name_ar": "عصب", "default_type": "DIVISIBLE", "default_unit": "unit"},
        headers=admin_headers,
    )
    assert cat_res.status_code == 200, cat_res.text
    cat_id = cat_res.json()["data"]["id"]

    wh1_res = client.post(
        "/api/v1/inventory/warehouses",
        json={"name": "Main Store", "type": "MAIN"},
        headers=admin_headers,
    )
    wh2_res = client.post(
        "/api/v1/inventory/warehouses",
        json={"name": "Clinic Room", "type": "CLINIC"},
        headers=admin_headers,
    )
    assert wh1_res.status_code == 200 and wh2_res.status_code == 200
    wh1_id = wh1_res.json()["data"]["id"]
    wh2_id = wh2_res.json()["data"]["id"]

    # QA-13: invalid packaging_ratio=0 and alert_threshold=-3 rejected 422
    bad_mat = client.post(
        "/api/v1/inventory/materials",
        json={
            "name": "Bad Material",
            "type": "DIVISIBLE",
            "base_unit": "g",
            "packaging_ratio": 0,
            "alert_threshold": -3,
            "category_id": cat_id,
        },
        headers=admin_headers,
    )
    assert bad_mat.status_code == 422

    # QA-10: create material with valid category_id returns 200 with category loaded
    mat_res = client.post(
        "/api/v1/inventory/materials",
        json={
            "name": "Gutta Percha",
            "type": "DIVISIBLE",
            "base_unit": "pack",
            "packaging_ratio": 10.0,
            "alert_threshold": 5,
            "category_id": cat_id,
        },
        headers=admin_headers,
    )
    assert mat_res.status_code == 200, mat_res.text
    mat_data = mat_res.json()["data"]
    assert mat_data["category"]["id"] == cat_id
    mat_id = mat_data["id"]

    # Sibling endpoints: PUT material & GET category materials
    upd_res = client.put(
        f"/api/v1/inventory/materials/{mat_id}",
        json={"alert_threshold": 8},
        headers=admin_headers,
    )
    assert upd_res.status_code == 200, upd_res.text
    assert upd_res.json()["data"]["category"]["id"] == cat_id

    cat_mats = client.get(f"/api/v1/inventory/categories/{cat_id}/materials", headers=admin_headers)
    assert cat_mats.status_code == 200, cat_mats.text
    assert cat_mats.json()["data"][0]["category"]["id"] == cat_id

    # QA-13: negative receive & consume rejected 422
    bad_recv = client.post(
        "/api/v1/inventory/receive",
        json={
            "material_id": mat_id,
            "warehouse_id": wh1_id,
            "quantity": -5,
            "batch": {"batch_number": "B-NEG", "expiry_date": "2028-01-01", "cost_per_unit": "2.50"},
        },
        headers=admin_headers,
    )
    assert bad_recv.status_code == 422

    bad_consume = client.post(
        "/api/v1/inventory/consume",
        json=[{"material_id": mat_id, "quantity": -2}],
        headers=admin_headers,
    )
    assert bad_consume.status_code == 422

    # QA-11: receive valid stock returns 200 with batch & warehouse populated
    recv_res = client.post(
        "/api/v1/inventory/receive",
        json={
            "material_id": mat_id,
            "warehouse_id": wh1_id,
            "quantity": 2,
            "batch": {"batch_number": "B-OK", "expiry_date": "2028-01-01", "cost_per_unit": "2.50"},
        },
        headers=admin_headers,
    )
    assert recv_res.status_code == 200, recv_res.text
    stock_item = recv_res.json()["data"]
    assert stock_item["warehouse"]["id"] == wh1_id
    assert stock_item["batch"]["material"]["id"] == mat_id

    # QA-12: transfer stock returns 200 and negative transfer returns 422
    bad_xfer = client.post(
        "/api/v1/inventory/transfer",
        json={"stock_item_id": stock_item["id"], "target_warehouse_id": wh2_id, "quantity": -1},
        headers=admin_headers,
    )
    assert bad_xfer.status_code == 422

    xfer_res = client.post(
        "/api/v1/inventory/transfer",
        json={"stock_item_id": stock_item["id"], "target_warehouse_id": wh2_id, "quantity": 4},
        headers=admin_headers,
    )
    assert xfer_res.status_code == 200, xfer_res.text
    assert xfer_res.json()["data"]["change_amount"] == 4


def test_qa14_qa15_prescription_validation_and_delete(client, db_session, test_patient, admin_headers):
    bad_empty = client.post(
        "/api/v1/prescriptions",
        json={"patient_id": test_patient.id, "medications": json.dumps([{"name": "", "dose": ""}])},
        headers=admin_headers,
    )
    assert bad_empty.status_code == 422

    bad_ws = client.post(
        "/api/v1/prescriptions",
        json={"patient_id": test_patient.id, "medications": "   "},
        headers=admin_headers,
    )
    assert bad_ws.status_code == 422

    ok_res = client.post(
        "/api/v1/prescriptions",
        json={
            "patient_id": test_patient.id,
            "medications": json.dumps([{"name": "Amoxicillin", "dose": "500mg"}]),
        },
        headers=admin_headers,
    )
    assert ok_res.status_code == 200, ok_res.text
    rx_id = ok_res.json()["data"]["id"]

    del_res = client.delete(f"/api/v1/prescriptions/{rx_id}", headers=admin_headers)
    assert del_res.status_code == 200, del_res.text
    assert del_res.json()["data"] == {"id": rx_id, "deleted": True}
    assert db_session.get(models.Prescription, rx_id) is None


def test_qa18_appointment_lab_and_user_validation(client, test_patient, admin_headers):
    # Appointment negative duration & nonsense status
    r_dur = client.post(
        "/api/v1/appointments",
        json={"patient_id": test_patient.id, "date_time": "2026-12-01T10:00:00", "duration_minutes": -30},
        headers=admin_headers,
    )
    assert r_dur.status_code == 422

    r_bad_status = client.post(
        "/api/v1/appointments",
        json={"patient_id": test_patient.id, "date_time": "2026-12-01T11:00:00", "status": "nonsense"},
        headers=admin_headers,
    )
    assert r_bad_status.status_code == 422

    r_ok_appt = client.post(
        "/api/v1/appointments",
        json={"patient_id": test_patient.id, "date_time": "2026-12-01T12:00:00", "status": "Scheduled"},
        headers=admin_headers,
    )
    assert r_ok_appt.status_code == 201, r_ok_appt.text
    appt_id = r_ok_appt.json()["data"]["id"]

    r_put_status = client.put(
        f"/api/v1/appointments/{appt_id}/status",
        params={"status": "nonsense"},
        headers=admin_headers,
    )
    assert r_put_status.status_code == 422

    # Lab blank name & nonsense order status
    r_bad_lab = client.post("/api/v1/laboratories", json={"name": "   "}, headers=admin_headers)
    assert r_bad_lab.status_code == 422

    r_lab = client.post("/api/v1/laboratories", json={"name": "Crown Lab"}, headers=admin_headers)
    assert r_lab.status_code == 200, r_lab.text
    lab_id = r_lab.json()["data"]["id"]

    r_order = client.post(
        "/api/v1/lab-orders",
        json={"patient_id": test_patient.id, "laboratory_id": lab_id, "work_type": "Crown", "status": "pending"},
        headers=admin_headers,
    )
    assert r_order.status_code == 200, r_order.text
    order_id = r_order.json()["data"]["id"]

    r_bad_order_upd = client.put(
        f"/api/v1/lab-orders/{order_id}",
        json={"status": "nonsense"},
        headers=admin_headers,
    )
    assert r_bad_order_upd.status_code == 422

    # User nonsense role 422, super_admin still 403
    r_bad_role = client.post(
        "/api/v1/users/register",
        json={"username": "qa_bad_role", "password": "Valid#Password99!", "role": "nonsense"},
        headers=admin_headers,
    )
    assert r_bad_role.status_code == 422

    r_super = client.post(
        "/api/v1/users/register",
        json={"username": "qa_super_role", "password": "Valid#Password99!", "role": "super_admin"},
        headers=admin_headers,
    )
    assert r_super.status_code == 403


@pytest.mark.asyncio
async def test_qa21_deleted_staff_excluded_from_payroll_unless_paid_in_month(async_db_session):
    tenant = models.Tenant(name="Payroll Clinic", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    admin = models.User(
        username="pay_admin",
        email="pay_admin@example.com",
        hashed_password=get_password_hash("Valid#Pass1"),
        role="admin",
        tenant_id=tenant.id,
        is_active=True,
        is_deleted=False,
    )
    active_staff = models.User(
        username="active_rec",
        email="active_rec@example.com",
        hashed_password=get_password_hash("Valid#Pass1"),
        role="receptionist",
        tenant_id=tenant.id,
        fixed_salary=3000.0,
        is_active=True,
        is_deleted=False,
    )
    deleted_unpaid = models.User(
        username="deleted_unpaid",
        email="deleted_unpaid@example.com",
        hashed_password=get_password_hash("Valid#Pass1"),
        role="receptionist",
        tenant_id=tenant.id,
        fixed_salary=4000.0,
        is_active=False,
        is_deleted=True,
    )
    deleted_paid = models.User(
        username="deleted_paid",
        email="deleted_paid@example.com",
        hashed_password=get_password_hash("Valid#Pass1"),
        role="nurse",
        tenant_id=tenant.id,
        fixed_salary=2500.0,
        is_active=False,
        is_deleted=True,
    )
    async_db_session.add_all([admin, active_staff, deleted_unpaid, deleted_paid])
    await async_db_session.flush()

    async_db_session.add(
        models.SalaryPayment(
            tenant_id=tenant.id,
            user_id=deleted_paid.id,
            month="2026-09",
            amount=2500.0,
            is_partial=False,
            days_worked=30,
        )
    )
    await async_db_session.commit()

    svc = AccountingService(async_db_session, tenant.id)

    staff_rev = await svc.get_staff_list_revenue()
    rev_ids = {s["id"] for s in staff_rev}
    assert active_staff.id in rev_ids
    assert deleted_unpaid.id not in rev_ids
    assert deleted_paid.id not in rev_ids

    dues_start, dues_end = svc.parse_date_range("2026-10-01", "2026-10-31")
    dues, total_dues = await svc.calculate_staff_dues(
        dues_start,
        dues_end,
        total_appointments=0,
    )
    assert [d["id"] for d in dues] == [active_staff.id]
    assert total_dues == 3000.0

    # Current month: deleted employees without payments are excluded
    oct_payroll = await svc.get_salary_status_for_month("2026-10")
    assert [e["id"] for e in oct_payroll["employees"]] == [active_staff.id]

    # Historical month with recorded SalaryPayment retains paid history, never unpaid deleted staff
    sep_payroll = await svc.get_salary_status_for_month("2026-09")
    sep_ids = {e["id"] for e in sep_payroll["employees"]}
    assert active_staff.id in sep_ids
    assert deleted_paid.id in sep_ids
    assert deleted_unpaid.id not in sep_ids

    # New payment for deleted employee is rejected
    pay_res = await svc.process_salary_payment(deleted_unpaid.id, admin, "2026-10", 500.0, False, 30, "test")
    assert "error" in pay_res


def test_qa23_upload_rejects_fake_png_and_accepts_real_png(client, test_patient, admin_headers, tmp_path, monkeypatch):
    from backend.services import file_service

    monkeypatch.setattr(file_service, "_get_upload_root", lambda: tmp_path)

    # 1. Spoofed ASCII payload claiming image/png -> rejected 400
    fake_res = client.post(
        f"/api/v1/upload?patient_id={test_patient.id}",
        files={"file": ("fake.png", b"not actually a png file", "image/png")},
        headers=admin_headers,
    )
    assert fake_res.status_code == 400, fake_res.text

    # 2. SVG still rejected 400
    svg_res = client.post(
        f"/api/v1/upload?patient_id={test_patient.id}",
        files={"file": ("xss.svg", b"<svg></svg>", "image/svg+xml")},
        headers=admin_headers,
    )
    assert svg_res.status_code == 400

    # 3. Empty file still rejected 400
    empty_res = client.post(
        f"/api/v1/upload?patient_id={test_patient.id}",
        files={"file": ("empty.png", b"", "image/png")},
        headers=admin_headers,
    )
    assert empty_res.status_code == 400

    # 4. Real PNG accepted 200
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(buf, format="PNG")
    ok_res = client.post(
        f"/api/v1/upload?patient_id={test_patient.id}",
        files={"file": ("real.png", buf.getvalue(), "image/png")},
        headers=admin_headers,
    )
    assert ok_res.status_code == 200, ok_res.text
    assert ok_res.json()["storage_status"] == "ready"


def test_qa25_next_visit_request_event_allows_archive_export(
    client, db_session, test_tenant, test_patient, admin_headers, monkeypatch
):
    _enable_native_writes(db_session, test_tenant.id)
    monkeypatch.setenv("TENANT_BACKUP_KEY_ID", "synthetic-key")
    monkeypatch.setenv("TENANT_BACKUP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"a" * 32).decode())
    monkeypatch.setenv("DENTIX_INSTALLATION_ID", "synthetic-installation")
    monkeypatch.setenv("TENANT_BACKUP_MAX_BYTES", "1000000")
    monkeypatch.setattr("backend.routers.tenant_backups._revision", AsyncMock(return_value="synthetic-revision"))

    # Create a next-visit request without associated_work_item_ids
    nvr_res = client.post(
        f"/api/v1/patients/{test_patient.id}/next-visit-requests",
        json={"reason": "Routine follow-up", "suggested_duration_minutes": 30},
        headers=admin_headers,
    )
    assert nvr_res.status_code == 201, nvr_res.text

    ev = (
        db_session.query(models.ClinicalEvent)
        .filter_by(tenant_id=test_tenant.id, event_type="next_visit_request_created")
        .first()
    )
    assert ev is not None
    assert ev.payload["associated_work_item_ids"] == []

    # Backward-compatibility check: legacy event with null list also remaps cleanly
    remapped_null = remap_event_payload({"associated_work_item_ids": None}, {"clinical_work_items": {}})
    assert remapped_null == {"associated_work_item_ids": None}

    # Archive export succeeds 200
    archive_res = client.get("/api/v1/settings/backup/archive", headers=admin_headers)
    assert archive_res.status_code == 200, archive_res.text
