"""
Regression tests for PR-01 F1: AI Patient Visibility & Cross-Tenant Boundaries.

Verifies that AI execution paths (autocomplete, tool execution, lookup, reads, mutations)
enforce canonical patient visibility and tenant isolation.
"""

import pytest
from unittest.mock import MagicMock
from backend import models
from backend.auth import create_access_token, get_password_hash
from backend.ai.executor import ToolExecutor
from backend.utils.patient_search_normalization import (
    normalize_patient_name_for_search,
    patient_phone_search_hash,
)


def _make_patient(*, tenant_id, name, phone, assigned_doctor_id, notes=""):
    return models.Patient(
        tenant_id=tenant_id,
        name=name,
        name_search_normalized=normalize_patient_name_for_search(name),
        phone=phone,
        phone_search_hash=patient_phone_search_hash(phone),
        age=35,
        medical_history="Hypertension",
        notes=notes,
        assigned_doctor_id=assigned_doctor_id,
    )


@pytest.fixture
def f1_setup(db_session):
    """
    Synthetic 2-tenant fixture:
    Tenant A:
      - Doctor A (visibility_mode: all_assigned)
      - Doctor B (visibility_mode: all_assigned)
      - Admin A (role: admin)
      - Reception A (role: receptionist)
      - Patient A1: assigned to Doctor A ("Omar Khaled", phone: "01011111111")
      - Patient B1: assigned to Doctor B ("Omar Farouk", phone: "01022222222") (ambiguity with A1)
      - Patient B_Secret: assigned to Doctor B ("Tarek Restricted", phone: "01033333333")
    Tenant B:
      - Patient B_OtherTenant: ("Omar Khaled", phone: "01044444444")
    """
    tenant_a = models.Tenant(name="Clinic A", is_active=True)
    tenant_b = models.Tenant(name="Clinic B", is_active=True)
    db_session.add_all([tenant_a, tenant_b])
    db_session.commit()
    db_session.refresh(tenant_a)
    db_session.refresh(tenant_b)

    doc_a = models.User(
        username="doctor_a_f1",
        email="doc_a_f1@test.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_a.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    doc_b = models.User(
        username="doctor_b_f1",
        email="doc_b_f1@test.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_a.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    admin_a = models.User(
        username="admin_a_f1",
        email="admin_a_f1@test.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_a.id,
        is_active=True,
    )
    reception_a = models.User(
        username="reception_a_f1",
        email="reception_a_f1@test.com",
        hashed_password=get_password_hash("pass123"),
        role="receptionist",
        tenant_id=tenant_a.id,
        is_active=True,
    )
    db_session.add_all([doc_a, doc_b, admin_a, reception_a])
    db_session.commit()
    for u in (doc_a, doc_b, admin_a, reception_a):
        db_session.refresh(u)

    patient_a1 = _make_patient(
        tenant_id=tenant_a.id,
        name="Omar Khaled",
        phone="01011111111",
        assigned_doctor_id=doc_a.id,
    )
    patient_b1 = _make_patient(
        tenant_id=tenant_a.id,
        name="Omar Farouk",
        phone="01022222222",
        assigned_doctor_id=doc_b.id,
    )
    patient_b_secret = _make_patient(
        tenant_id=tenant_a.id,
        name="Tarek Restricted",
        phone="01033333333",
        assigned_doctor_id=doc_b.id,
        notes="Initial note",
    )
    patient_tenant_b = _make_patient(
        tenant_id=tenant_b.id,
        name="Omar Khaled",
        phone="01044444444",
        assigned_doctor_id=9999,
    )
    db_session.add_all([patient_a1, patient_b1, patient_b_secret, patient_tenant_b])
    db_session.commit()
    for p in (patient_a1, patient_b1, patient_b_secret, patient_tenant_b):
        db_session.refresh(p)

    # Add treatment and balance for patients
    t_a = models.Treatment(
        tenant_id=tenant_a.id,
        patient_id=patient_a1.id,
        doctor_id=doc_a.id,
        procedure="Scaling",
        cost=500.0,
        discount=0.0,
        is_deleted=False,
    )
    t_b = models.Treatment(
        tenant_id=tenant_a.id,
        patient_id=patient_b_secret.id,
        doctor_id=doc_b.id,
        procedure="Root Canal",
        cost=1500.0,
        discount=0.0,
        is_deleted=False,
    )
    lab_b = models.LabOrder(
        tenant_id=tenant_a.id,
        patient_id=patient_b_secret.id,
        doctor_id=doc_b.id,
        work_type="Zirconia Crown",
        cost=700.0,
        status="sent",
    )
    db_session.add_all([t_a, t_b, lab_b])
    db_session.commit()

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "doc_a": doc_a,
        "doc_b": doc_b,
        "admin_a": admin_a,
        "reception_a": reception_a,
        "patient_a1": patient_a1,
        "patient_b1": patient_b1,
        "patient_b_secret": patient_b_secret,
        "patient_tenant_b": patient_tenant_b,
    }


def _auth_header(user):
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


def test_doctor_cannot_discover_restricted_patient_via_autocomplete(client, f1_setup):
    """Doctor A should not see Doctor B's restricted patients in autocomplete results."""
    doc_a = f1_setup["doc_a"]
    headers = _auth_header(doc_a)

    # Search for 'Omar' which matches Patient A1 (visible) and Patient B1 (restricted to Doc B)
    res = client.get("/api/v1/ai/autocomplete?q=Omar", headers=headers)
    assert res.status_code == 200
    data = res.json()
    patients = data.get("patients", [])

    returned_ids = {p["id"] for p in patients}
    assert f1_setup["patient_a1"].id in returned_ids
    # Patient B1 and Patient Tenant B must NOT be visible
    assert f1_setup["patient_b1"].id not in returned_ids
    assert f1_setup["patient_tenant_b"].id not in returned_ids

    # Search for 'Tarek' which only matches Patient B_Secret (assigned to Doc B)
    res_tarek = client.get("/api/v1/ai/autocomplete?q=Tarek", headers=headers)
    assert res_tarek.status_code == 200
    tarek_patients = res_tarek.json().get("patients", [])
    assert len(tarek_patients) == 0


@pytest.mark.asyncio
async def test_doctor_cannot_search_or_read_restricted_patient_via_ai_tools(async_db_session, f1_setup):
    """ToolExecutor for Doctor A must not return restricted patients in search or file lookup."""
    doc_a = f1_setup["doc_a"]
    executor = ToolExecutor(async_db_session, doc_a)

    # 1. search_patients
    search_res = await executor.execute("search_patients", {"query": "Omar"})
    assert search_res.get("success") is True
    found_ids = {p["id"] for p in search_res.get("patients", [])}
    assert f1_setup["patient_a1"].id in found_ids
    assert f1_setup["patient_b1"].id not in found_ids
    assert f1_setup["patient_tenant_b"].id not in found_ids

    # 2. get_patient_file for restricted patient
    file_res = await executor.execute("get_patient_file", {"patient_name": "Tarek Restricted"})
    # Must fail or return not found without leaking patient file
    assert file_res.get("success") is not True or "patient" not in file_res

    # 3. summarize_patient for restricted patient
    sum_res = await executor.execute("summarize_patient", {"patient_name": "Tarek Restricted"})
    assert sum_res.get("success") is not True or "summary_data" not in sum_res

    # 4. get_patients_with_balance - Doctor has no RECEIVABLE_READ permission
    bal_res = await executor.execute("get_patients_with_balance", {})
    assert bal_res.get("success") is False
    assert bal_res.get("error_code") == "permission_denied"


@pytest.mark.asyncio
async def test_doctor_cannot_leak_restricted_patient_via_ambiguous_names(async_db_session, f1_setup):
    """When Doctor A searches ambiguous name 'Omar', restricted Patient B1 must not appear in candidate list."""
    doc_a = f1_setup["doc_a"]
    executor = ToolExecutor(async_db_session, doc_a)

    # get_patient_file with ambiguous name
    file_res = await executor.execute("get_patient_file", {"patient_name": "Omar"})
    # If multiple candidates are returned, none of them may be Doctor B's patient
    if file_res.get("multiple"):
        candidate_ids = {p["id"] for p in file_res.get("patients", [])}
        assert f1_setup["patient_b1"].id not in candidate_ids
        assert f1_setup["patient_tenant_b"].id not in candidate_ids


@pytest.mark.asyncio
async def test_doctor_cannot_read_clinical_history_of_restricted_patient(async_db_session, f1_setup):
    """Doctor A calling get_recent_treatments or get_lab_orders must not receive restricted patient clinical data."""
    doc_a = f1_setup["doc_a"]
    executor = ToolExecutor(async_db_session, doc_a)

    treatments_res = await executor.execute("get_recent_treatments", {})
    assert treatments_res.get("success") is not False
    treatments = treatments_res.get("treatments", [])
    # Patient B_Secret's treatment ("Root Canal") must not appear
    for t in treatments:
        assert t.get("procedure") != "Root Canal"
        assert t.get("patient_name") != "Tarek Restricted"

    lab_res = await executor.execute("get_lab_orders", {})
    assert lab_res.get("success") is not False
    orders = lab_res.get("orders", [])
    for o in orders:
        assert o.get("work_type") != "Zirconia Crown"
        assert o.get("patient_name") != "Tarek Restricted"


@pytest.mark.asyncio
async def test_doctor_cannot_mutate_restricted_patient_clinical_data(async_db_session, f1_setup):
    """Doctor A cannot add notes, treatments, or update tooth status for restricted patient."""
    doc_a = f1_setup["doc_a"]
    executor = ToolExecutor(async_db_session, doc_a)

    secret_patient = f1_setup["patient_b_secret"]
    orig_notes = secret_patient.notes

    # 1. record_medical_note on restricted patient
    note_res = await executor.execute(
        "record_medical_note",
        {"patient_name": "Tarek Restricted", "content": "Doctor A unauthorized note"},
    )
    # Must fail or be denied
    assert note_res.get("action") != "note_recorded"

    # Refresh patient from db
    reloaded_patient = await async_db_session.get(models.Patient, secret_patient.id)
    assert "Doctor A unauthorized note" not in (reloaded_patient.notes or "")
    assert reloaded_patient.notes == orig_notes

    # 2. update_tooth_status on restricted patient
    tooth_res = await executor.execute(
        "update_tooth_status",
        {"patient_name": "Tarek Restricted", "tooth_number": 16, "condition": "Decayed"},
    )
    assert tooth_res.get("action") != "tooth_updated"

    # 3. add_treatment on restricted patient
    treat_res = await executor.execute(
        "add_treatment",
        {"patient_name": "Tarek Restricted", "procedure": "Unauthorized Extraction", "cost": 300},
    )
    assert treat_res.get("action") != "treatment_created"


@pytest.mark.asyncio
async def test_admin_and_reception_retain_canonical_patient_access(async_db_session, f1_setup):
    """Admin and reception users must retain access to clinic patients in AI tools."""
    admin_a = f1_setup["admin_a"]
    reception_a = f1_setup["reception_a"]

    admin_executor = ToolExecutor(async_db_session, admin_a)
    reception_executor = ToolExecutor(async_db_session, reception_a)

    # Admin searches 'Omar' -> should see both patient_a1 and patient_b1 (same tenant)
    admin_res = await admin_executor.execute("search_patients", {"query": "Omar"})
    admin_ids = {p["id"] for p in admin_res.get("patients", [])}
    assert f1_setup["patient_a1"].id in admin_ids
    assert f1_setup["patient_b1"].id in admin_ids
    # But never cross-tenant:
    assert f1_setup["patient_tenant_b"].id not in admin_ids

    # Reception searches 'Omar' -> should also see both patients in Tenant A
    rec_res = await reception_executor.execute("search_patients", {"query": "Omar"})
    rec_ids = {p["id"] for p in rec_res.get("patients", [])}
    assert f1_setup["patient_a1"].id in rec_ids
    assert f1_setup["patient_b1"].id in rec_ids
    assert f1_setup["patient_tenant_b"].id not in rec_ids

    # Reception has RECEIVABLE_READ -> get_patients_with_balance succeeds
    rec_bal = await reception_executor.execute("get_patients_with_balance", {})
    assert rec_bal.get("success") is True
    rec_bal_ids = {p["id"] for p in rec_bal.get("patients", [])}
    assert f1_setup["patient_tenant_b"].id not in rec_bal_ids
