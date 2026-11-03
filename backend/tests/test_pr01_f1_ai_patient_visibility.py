"""
Regression tests for PR-01 F1: AI Patient Visibility & Cross-Tenant Boundaries.

Verifies that AI execution paths (autocomplete, tool execution, lookup, reads, mutations)
enforce canonical patient visibility and tenant isolation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from sqlalchemy import select, func
from backend import models
from backend.auth import create_access_token, get_password_hash
from backend.ai.executor import ToolExecutor
from backend.core.permissions import Permission, has_permission, PatientVisibilityMode
from backend.services.visibility_service import get_visibility_service
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
    """
    R5: Doctor A cannot add notes, treatments, or update tooth status for restricted patient.
    Checks:
    - Established rejection outcome
    - No treatments added to database
    - No clinical notes mutated
    - No tooth status records added
    - Positive permitted case passes for authorized visible patient
    """
    doc_a = f1_setup["doc_a"]
    executor = ToolExecutor(async_db_session, doc_a)

    secret_patient = f1_setup["patient_b_secret"]
    orig_notes = secret_patient.notes

    # Snapshot baseline counts before mutations
    treatments_before = (
        await async_db_session.execute(
            select(func.count(models.Treatment.id)).where(
                models.Treatment.patient_id == secret_patient.id
            )
        )
    ).scalar() or 0

    teeth_before = (
        await async_db_session.execute(
            select(func.count(models.ToothStatus.id)).where(
                models.ToothStatus.patient_id == secret_patient.id
            )
        )
    ).scalar() or 0

    # 1. record_medical_note on restricted patient
    note_res = await executor.execute(
        "record_medical_note",
        {"patient_name": "Tarek Restricted", "content": "Doctor A unauthorized note"},
    )
    assert note_res.get("action") != "note_recorded"

    reloaded_patient = await async_db_session.get(models.Patient, secret_patient.id)
    assert "Doctor A unauthorized note" not in (reloaded_patient.notes or "")
    assert reloaded_patient.notes == orig_notes

    # 2. update_tooth_status on restricted patient
    tooth_res = await executor.execute(
        "update_tooth_status",
        {"patient_name": "Tarek Restricted", "tooth_number": 16, "condition": "Decayed"},
    )
    assert tooth_res.get("action") != "tooth_updated"
    teeth_after = (
        await async_db_session.execute(
            select(func.count(models.ToothStatus.id)).where(
                models.ToothStatus.patient_id == secret_patient.id
            )
        )
    ).scalar() or 0
    assert teeth_after == teeth_before

    # 3. add_treatment on restricted patient
    treat_res = await executor.execute(
        "add_treatment",
        {"patient_name": "Tarek Restricted", "procedure": "Unauthorized Extraction", "cost": 300},
    )
    # Established success action is "treatment_added"; must NOT be returned
    assert treat_res.get("action") != "treatment_added"
    assert treat_res.get("requires_patient") is True or treat_res.get("error") == "not_found"

    treatments_after = (
        await async_db_session.execute(
            select(func.count(models.Treatment.id)).where(
                models.Treatment.patient_id == secret_patient.id
            )
        )
    ).scalar() or 0
    assert treatments_after == treatments_before

    # Positive permitted case: visible patient can be mutated
    vis_patient = f1_setup["patient_a1"]
    perm_note_res = await executor.execute(
        "record_medical_note",
        {"patient_name": vis_patient.name, "content": "Authorized Doctor Note"},
    )
    assert perm_note_res.get("action") == "note_recorded"

    perm_treat_res = await executor.execute(
        "add_treatment",
        {"patient_name": vis_patient.name, "procedure": "Authorized Scaling", "cost": 250},
    )
    assert perm_treat_res.get("action") == "treatment_added"


@pytest.mark.asyncio
async def test_doctor_appointment_tool_obeys_canonical_visibility(async_db_session, f1_setup):
    """
    R2: get_appointments must intersect doctor schedule filtering with canonical patient
    visibility across all three visibility modes:
    - all_assigned
    - appointments_only
    - mixed
    Hidden patients' names, IDs, notes, counts, and suggestions must never be disclosed.
    """
    doc_a = f1_setup["doc_a"]  # all_assigned
    hidden_patient = f1_setup["patient_b_secret"]
    visible_patient_a = f1_setup["patient_a1"]
    tenant_id = f1_setup["tenant_a"].id

    # --- Mode 1: all_assigned (doc_a) ---
    vis_a = get_visibility_service(async_db_session, doc_a, tenant_id)
    assert not await vis_a.can_view_patient(hidden_patient.id)
    assert await vis_a.can_view_patient(visible_patient_a.id)

    today_time = datetime.now().replace(hour=11, minute=30, second=0, microsecond=0)
    vis_appt_a = models.Appointment(
        tenant_id=tenant_id,
        patient_id=visible_patient_a.id,
        doctor_id=doc_a.id,
        date_time=today_time,
        status="Scheduled",
        notes="Visible appointment notes",
    )
    hidden_appt = models.Appointment(
        tenant_id=tenant_id,
        patient_id=hidden_patient.id,
        doctor_id=doc_a.id,
        date_time=today_time,
        status="Scheduled",
        notes="Confidential appointment notes",
    )
    async_db_session.add_all([vis_appt_a, hidden_appt])
    await async_db_session.commit()

    executor_a = ToolExecutor(async_db_session, doc_a)
    result_a = await executor_a.execute("get_appointments", {"date": "today"})
    assert hidden_patient.name not in str(result_a)
    assert "Confidential appointment notes" not in str(result_a)
    disclosed_ids_a = [a["id"] for a in result_a.get("appointments", [])]
    assert hidden_appt.id not in disclosed_ids_a
    assert any(a["patient_name"] == visible_patient_a.name for a in result_a.get("appointments", []))

    # --- Mode 2: appointments_only ---
    doc_appt_only = models.User(
        username="doc_appt_only_r2",
        email="doc_appt_only_r2@test.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_id,
        patient_visibility_mode="appointments_only",
        is_active=True,
    )
    doc_mixed = models.User(
        username="doc_mixed_r2",
        email="doc_mixed_r2@test.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_id,
        patient_visibility_mode="mixed",
        is_active=True,
    )
    async_db_session.add_all([doc_appt_only, doc_mixed])
    await async_db_session.commit()
    await async_db_session.refresh(doc_appt_only)
    await async_db_session.refresh(doc_mixed)

    # Give doc_appt_only an appointment with visible_patient_a; hidden_patient has NO appointment with doc_appt_only
    appt_b_vis = models.Appointment(
        tenant_id=tenant_id,
        patient_id=visible_patient_a.id,
        doctor_id=doc_appt_only.id,
        date_time=today_time,
        status="Scheduled",
        notes="Doc ApptOnly visible appointment",
    )
    async_db_session.add(appt_b_vis)
    await async_db_session.commit()

    vis_appt_only = get_visibility_service(async_db_session, doc_appt_only, tenant_id)
    assert await vis_appt_only.can_view_patient(visible_patient_a.id)
    assert not await vis_appt_only.can_view_patient(hidden_patient.id)

    executor_b = ToolExecutor(async_db_session, doc_appt_only)
    result_b = await executor_b.execute("get_appointments", {"date": "today"})
    assert visible_patient_a.name in str(result_b)
    assert hidden_patient.name not in str(result_b)

    # --- Mode 3: mixed ---
    patient_c_assigned = models.Patient(
        tenant_id=tenant_id,
        name="Salma Mixed Assigned",
        name_search_normalized=normalize_patient_name_for_search("Salma Mixed Assigned"),
        phone="01000000099",
        phone_search_hash=patient_phone_search_hash("01000000099"),
        age=29,
        assigned_doctor_id=doc_mixed.id,
    )
    async_db_session.add(patient_c_assigned)
    await async_db_session.commit()
    await async_db_session.refresh(patient_c_assigned)

    appt_c = models.Appointment(
        tenant_id=tenant_id,
        patient_id=patient_c_assigned.id,
        doctor_id=doc_mixed.id,
        date_time=today_time,
        status="Scheduled",
        notes="Doc Mixed appointment",
    )
    async_db_session.add(appt_c)
    await async_db_session.commit()

    vis_mixed = get_visibility_service(async_db_session, doc_mixed, tenant_id)
    assert await vis_mixed.can_view_patient(patient_c_assigned.id)
    assert not await vis_mixed.can_view_patient(hidden_patient.id)

    executor_c = ToolExecutor(async_db_session, doc_mixed)
    result_c = await executor_c.execute("get_appointments", {"date": "today"})
    assert patient_c_assigned.name in str(result_c)
    assert hidden_patient.name not in str(result_c)


@pytest.mark.asyncio
async def test_patient_summary_respects_receivable_permission(async_db_session, f1_setup):
    """
    R3: summarize_patient requires PATIENT_READ for clinical summary,
    and RECEIVABLE_READ for financial balance output (total_due).
    Doctor without RECEIVABLE_READ must NOT receive total_due or trigger balance aggregation.
    """
    from decimal import Decimal
    from sqlalchemy import event

    doc_a = f1_setup["doc_a"]
    rec_a = f1_setup["reception_a"]
    patient = f1_setup["patient_a1"]

    assert has_permission(doc_a.role, Permission.PATIENT_READ)
    assert not has_permission(doc_a.role, Permission.RECEIVABLE_READ)
    assert has_permission(rec_a.role, Permission.RECEIVABLE_READ)

    # Add a treatment and a payment for patient
    t = models.Treatment(
        tenant_id=patient.tenant_id,
        patient_id=patient.id,
        procedure="Crown",
        cost=Decimal("1000.00"),
        discount=Decimal("0.00"),
        date=datetime.now().date(),
    )
    p = models.Payment(
        tenant_id=patient.tenant_id,
        patient_id=patient.id,
        amount=Decimal("500.00"),
        date=datetime.now().date(),
    )
    async_db_session.add_all([t, p])
    await async_db_session.commit()

    # Doctor summarizes patient — spy on SQL to verify NO payments query is executed
    doc_sql = []

    def _capture_doc_sql(conn, cursor, statement, parameters, context, executemany):
        doc_sql.append(statement)

    event.listen(async_db_session.sync_session.bind, "before_cursor_execute", _capture_doc_sql)
    try:
        doc_executor = ToolExecutor(async_db_session, doc_a)
        doc_result = await doc_executor.execute("summarize_patient", {"patient_name": patient.name})
    finally:
        event.remove(async_db_session.sync_session.bind, "before_cursor_execute", _capture_doc_sql)

    assert doc_result.get("success") is True
    summary_data = doc_result.get("summary_data", {})
    # Clinical fields are present
    assert "age" in summary_data
    assert "recent_procedures" in summary_data
    # Financial total_due MUST be absent and payments table MUST NOT be queried
    assert "total_due" not in summary_data
    assert not any("payments" in stmt.lower() for stmt in doc_sql), (
        f"Unexpected payments query executed for doctor without RECEIVABLE_READ: {doc_sql}"
    )

    # Receptionist summarizes patient (has RECEIVABLE_READ) -> payments queried and exact Decimal returned
    rec_sql = []

    def _capture_rec_sql(conn, cursor, statement, parameters, context, executemany):
        rec_sql.append(statement)

    event.listen(async_db_session.sync_session.bind, "before_cursor_execute", _capture_rec_sql)
    try:
        rec_executor = ToolExecutor(async_db_session, rec_a)
        rec_result = await rec_executor.execute("summarize_patient", {"patient_name": patient.name})
    finally:
        event.remove(async_db_session.sync_session.bind, "before_cursor_execute", _capture_rec_sql)

    assert rec_result.get("success") is True
    assert "total_due" in rec_result.get("summary_data", {})
    assert any("payments" in stmt.lower() for stmt in rec_sql)
    # patient_a1 has t_a (500) + t (1000) - p (500) = 1000.00 balance
    assert rec_result["summary_data"]["total_due"] == Decimal("1000.00")


@pytest.mark.asyncio
async def test_receivable_summary_preserves_exact_decimal_money(async_db_session, f1_setup):
    """
    Standards check: Decimal("0.10") + Decimal("0.20") must equal exact Decimal("0.30"),
    never binary float 0.30000000000000004.
    """
    from decimal import Decimal
    from backend.services.patient_service import PatientService

    rec_a = f1_setup["reception_a"]
    tenant_id = f1_setup["tenant_a"].id

    patient = models.Patient(
        tenant_id=tenant_id,
        name="Decimal Precision Patient",
        name_search_normalized=normalize_patient_name_for_search("Decimal Precision Patient"),
        phone="01055555555",
        phone_search_hash=patient_phone_search_hash("01055555555"),
        age=41,
        assigned_doctor_id=f1_setup["doc_a"].id,
    )
    async_db_session.add(patient)
    await async_db_session.commit()
    await async_db_session.refresh(patient)

    t1 = models.Treatment(
        tenant_id=tenant_id,
        patient_id=patient.id,
        procedure="Step 1",
        cost=Decimal("0.10"),
        discount=Decimal("0.00"),
        date=datetime.now().date(),
    )
    t2 = models.Treatment(
        tenant_id=tenant_id,
        patient_id=patient.id,
        procedure="Step 2",
        cost=Decimal("0.20"),
        discount=Decimal("0.00"),
        date=datetime.now().date(),
    )
    async_db_session.add_all([t1, t2])
    await async_db_session.commit()

    rec_executor = ToolExecutor(async_db_session, rec_a)
    adapter_result = await rec_executor.execute("summarize_patient", {"patient_name": patient.name})
    service_result = await PatientService(async_db_session, tenant_id).get_patient_summary_data(
        patient.name, include_financials=True
    )

    assert adapter_result["summary_data"]["total_due"] == Decimal("0.30")
    assert str(adapter_result["summary_data"]["total_due"]) != "0.30000000000000004"
    assert service_result["summary_data"]["total_due"] == Decimal("0.30")
    assert str(service_result["summary_data"]["total_due"]) != "0.30000000000000004"


@pytest.mark.asyncio
async def test_admin_and_reception_retain_canonical_patient_access(async_db_session, f1_setup):
    """
    Admin and reception users must retain access to clinic patients in AI tools,
    including reception payment recording (create_payment) and receivable reads,
    while doctors without RECEIVABLE_READ / PAYMENT_CREATE are denied.
    """
    admin_a = f1_setup["admin_a"]
    reception_a = f1_setup["reception_a"]
    doc_a = f1_setup["doc_a"]
    patient_a1 = f1_setup["patient_a1"]

    admin_executor = ToolExecutor(async_db_session, admin_a)
    reception_executor = ToolExecutor(async_db_session, reception_a)
    doc_executor = ToolExecutor(async_db_session, doc_a)

    # Admin searches 'Omar' -> should see both patient_a1 and patient_b1 (same tenant)
    admin_res = await admin_executor.execute("search_patients", {"query": "Omar"})
    admin_ids = {p["id"] for p in admin_res.get("patients", [])}
    assert patient_a1.id in admin_ids
    assert f1_setup["patient_b1"].id in admin_ids
    # But never cross-tenant:
    assert f1_setup["patient_tenant_b"].id not in admin_ids

    # Reception searches 'Omar' -> should also see both patients in Tenant A
    rec_res = await reception_executor.execute("search_patients", {"query": "Omar"})
    rec_ids = {p["id"] for p in rec_res.get("patients", [])}
    assert patient_a1.id in rec_ids
    assert f1_setup["patient_b1"].id in rec_ids
    assert f1_setup["patient_tenant_b"].id not in rec_ids

    # Reception has RECEIVABLE_READ -> get_patients_with_balance and get_financial_record succeed
    rec_bal = await reception_executor.execute("get_patients_with_balance", {})
    assert rec_bal.get("success") is True
    rec_bal_ids = {p["id"] for p in rec_bal.get("patients", [])}
    assert f1_setup["patient_tenant_b"].id not in rec_bal_ids

    rec_fin = await reception_executor.execute(
        "get_financial_record", {"patient_name": patient_a1.name}
    )
    assert rec_fin.get("success") is True
    assert "remaining" in rec_fin

    # Reception has PAYMENT_CREATE -> create_payment records a real payment in DB
    payments_before = (
        await async_db_session.execute(
            select(func.count(models.Payment.id)).where(models.Payment.patient_id == patient_a1.id)
        )
    ).scalar() or 0
    rec_pay = await reception_executor.execute(
        "create_payment", {"patient_name": patient_a1.name, "amount": 150}
    )
    assert rec_pay.get("success") is True
    assert rec_pay.get("action") == "payment_created"
    payments_after = (
        await async_db_session.execute(
            select(func.count(models.Payment.id)).where(models.Payment.patient_id == patient_a1.id)
        )
    ).scalar() or 0
    assert payments_after == payments_before + 1

    # Doctor lacks PAYMENT_CREATE and RECEIVABLE_READ -> denied on both tools
    doc_pay = await doc_executor.execute(
        "create_payment", {"patient_name": patient_a1.name, "amount": 150}
    )
    assert doc_pay.get("success") is False
    assert doc_pay.get("error_code") == "permission_denied"

    doc_fin = await doc_executor.execute(
        "get_financial_record", {"patient_name": patient_a1.name}
    )
    assert doc_fin.get("success") is False
    assert doc_fin.get("error_code") == "permission_denied"
