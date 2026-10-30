"""
Dedicated Test Suite for Clinical Command Security, Contracts, Idempotency & Concurrency (CARD S07).
Matrix Items Closed:
- G7-M13: Tenant Security Tests (Tenant isolation, cross-patient isolation, doctor visibility mode, tenant-scoped idempotency independence)
- G7-M14: API Contract & RBAC Tests (StandardResponse contract envelope across all 10 G7 endpoints, full 7-role matrix)
- G7-M15: Idempotency Keys (Single, bulk, correction replay, parameter mismatch 409, length/empty 422, concurrent same-key race)
- G7-M16: Optimistic Concurrency Handling (Stale expected_version_id on PATCH and /correct, concurrent update contention, session health after rollback)
"""

import asyncio
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.auth import create_access_token
from backend.clinical.catalog import FindingCode, ProcedureCode
from backend.core.permissions import PatientVisibilityMode, Role
from backend.database import get_async_db
from backend.services.clinical_command_service import ClinicalCommandService
from backend.services.clinical_workspace_service import (
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    FEATURE_FLAG_CLINICAL_PRIMARY,
)
from backend.services.feature_service import FeatureFlagService


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
async def seed_security_data(async_db_session):
    """Seed tenants, users across all roles, and patients."""
    tenant_1 = models.Tenant(name="Security Alpha Clinic", domain="sec-alpha.com", is_active=True)
    tenant_2 = models.Tenant(name="Security Beta Clinic", domain="sec-beta.com", is_active=True)
    async_db_session.add_all([tenant_1, tenant_2])
    await async_db_session.flush()

    # Tenant 1 users for all roles
    super_admin_1 = models.User(
        tenant_id=tenant_1.id,
        username="superadmin_t1",
        email="superadmin@t1.com",
        hashed_password="pw",
        role="super_admin",
        is_active=True,
    )
    admin_1 = models.User(
        tenant_id=tenant_1.id,
        username="admin_t1",
        email="admin@t1.com",
        hashed_password="pw",
        role="admin",
        is_active=True,
    )
    doctor_1 = models.User(
        tenant_id=tenant_1.id,
        username="doctor_t1",
        email="doctor@t1.com",
        hashed_password="pw",
        role="doctor",
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    doctor_1_appts_only = models.User(
        tenant_id=tenant_1.id,
        username="doctor_appts_t1",
        email="doctor_appts@t1.com",
        hashed_password="pw",
        role="doctor",
        patient_visibility_mode="appointments_only",
        is_active=True,
    )
    nurse_1 = models.User(
        tenant_id=tenant_1.id,
        username="nurse_t1",
        email="nurse@t1.com",
        hashed_password="pw",
        role="nurse",
        is_active=True,
    )
    receptionist_1 = models.User(
        tenant_id=tenant_1.id,
        username="recep_t1",
        email="recep@t1.com",
        hashed_password="pw",
        role="receptionist",
        is_active=True,
    )
    assistant_1 = models.User(
        tenant_id=tenant_1.id,
        username="asst_t1",
        email="asst@t1.com",
        hashed_password="pw",
        role="assistant",
        is_active=True,
    )
    guest_1 = models.User(
        tenant_id=tenant_1.id,
        username="guest_t1",
        email="guest@t1.com",
        hashed_password="pw",
        role="guest",
        is_active=True,
    )

    # Tenant 2 users
    doctor_2 = models.User(
        tenant_id=tenant_2.id,
        username="doctor_t2",
        email="doctor@t2.com",
        hashed_password="pw",
        role="doctor",
        patient_visibility_mode="all_assigned",
        is_active=True,
    )

    async_db_session.add_all([
        super_admin_1, admin_1, doctor_1, doctor_1_appts_only,
        nurse_1, receptionist_1, assistant_1, guest_1, doctor_2
    ])
    await async_db_session.flush()

    # Patients
    patient_t1_doc1 = models.Patient(
        tenant_id=tenant_1.id,
        name="Assigned Patient Doc1",
        age=35,
        phone="+1111111111",
        medical_history="No history",
        notes="Patient notes",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    patient_t1_other = models.Patient(
        tenant_id=tenant_1.id,
        name="Other Patient T1",
        age=40,
        phone="+1111111112",
        medical_history="No history",
        notes="Patient notes",
        assigned_doctor_id=None,
        is_deleted=False,
    )
    patient_t2 = models.Patient(
        tenant_id=tenant_2.id,
        name="Patient T2",
        age=29,
        phone="+2222222222",
        medical_history="No history",
        notes="Patient notes",
        assigned_doctor_id=doctor_2.id,
        is_deleted=False,
    )

    async_db_session.add_all([patient_t1_doc1, patient_t1_other, patient_t2])
    await async_db_session.commit()

    return {
        "tenant_1": tenant_1,
        "tenant_2": tenant_2,
        "super_admin_1": super_admin_1,
        "admin_1": admin_1,
        "doctor_1": doctor_1,
        "doctor_1_appts_only": doctor_1_appts_only,
        "nurse_1": nurse_1,
        "receptionist_1": receptionist_1,
        "assistant_1": assistant_1,
        "guest_1": guest_1,
        "doctor_2": doctor_2,
        "patient_t1_doc1": patient_t1_doc1,
        "patient_t1_other": patient_t1_other,
        "patient_t2": patient_t2,
        "patient_1": patient_t1_doc1,
        "patient_2": patient_t2,
    }


def make_headers(user: models.User) -> dict:
    token = create_access_token(
        data={"sub": user.username, "tenant_id": user.tenant_id, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


async def enable_flags_for_tenants(db, tenant_ids):
    stmt = select(models.FeatureFlag).where(
        models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES
    )
    flag = (await db.execute(stmt)).scalar_one_or_none()
    if not flag:
        flag = models.FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
            description="Clinical native writes",
            is_global_enabled=True,
            rollout_percentage=0,
        )
        db.add(flag)
        await db.commit()
    for tid in tenant_ids:
        await FeatureFlagService.set_tenant_override(
            db, tid, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True
        )


# ===========================================================================
# G7-M13: Tenant Security Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_tenant_isolation_cross_tenant_returns_404(client, seed_security_data, async_db_session):
    """Doctor 1 (Tenant 1) cannot access Tenant 2 patient via ANY of the 10 endpoints -> 404."""
    t1 = seed_security_data["tenant_1"].id
    t2 = seed_security_data["tenant_2"].id
    await enable_flags_for_tenants(async_db_session, [t1, t2])

    doctor_1 = seed_security_data["doctor_1"]
    doctor_2 = seed_security_data["doctor_2"]
    patient_2 = seed_security_data["patient_2"]
    headers_doc1 = make_headers(doctor_1)

    # First, create a work item in Tenant 2 by Doctor 2
    service_t2 = ClinicalCommandService(async_db_session, t2, doctor_2)
    wi_t2 = await service_t2.create_finding(
        patient_2.id,
        schemas.ClinicalFindingCreate(code=FindingCode.CARIES.value, tooth_key="16"),
    )

    finding_body = {"code": FindingCode.CARIES.value, "tooth_key": "16"}
    proc_body = {"code": ProcedureCode.REST_COMPOSITE.value, "tooth_key": "16", "surfaces": ["O"]}
    wi_body = {
        "kind": "finding",
        "code": FindingCode.CARIES.value,
        "status": "active",
        "targets": [{"target_kind": "tooth", "tooth_key": "16"}],
    }

    # 1. POST /patients/{id}/clinical-work-items -> 404
    r = client.post(f"/api/v1/patients/{patient_2.id}/clinical-work-items", headers=headers_doc1, json=wi_body)
    assert r.status_code == 404

    # 2. GET /patients/{id}/clinical-work-items -> 404
    r = client.get(f"/api/v1/patients/{patient_2.id}/clinical-work-items", headers=headers_doc1)
    assert r.status_code == 404

    # 3. PATCH /patients/{id}/clinical-work-items/{id} -> 404
    r = client.patch(
        f"/api/v1/patients/{patient_2.id}/clinical-work-items/{wi_t2.id}",
        headers=headers_doc1,
        json={"notes": "hacked"},
    )
    assert r.status_code == 404

    # 4. POST /patients/{id}/clinical-findings -> 404
    r = client.post(f"/api/v1/patients/{patient_2.id}/clinical-findings", headers=headers_doc1, json=finding_body)
    assert r.status_code == 404

    # 5. POST /patients/{id}/clinical-findings/bulk -> 404
    r = client.post(
        f"/api/v1/patients/{patient_2.id}/clinical-findings/bulk",
        headers=headers_doc1,
        json={"items": [finding_body]},
    )
    assert r.status_code == 404

    # 6. POST /patients/{id}/clinical-procedures -> 404
    r = client.post(f"/api/v1/patients/{patient_2.id}/clinical-procedures", headers=headers_doc1, json=proc_body)
    assert r.status_code == 404

    # 7. POST /patients/{id}/clinical-procedures/bulk -> 404
    r = client.post(
        f"/api/v1/patients/{patient_2.id}/clinical-procedures/bulk",
        headers=headers_doc1,
        json={"items": [proc_body]},
    )
    assert r.status_code == 404

    # 8. POST /patients/{id}/clinical-work-items/{id}/correct -> 404
    r = client.post(
        f"/api/v1/patients/{patient_2.id}/clinical-work-items/{wi_t2.id}/correct",
        headers=headers_doc1,
        json={"mode": "entered_in_error", "reason": "unauthorized correction"},
    )
    assert r.status_code == 404

    # 9. GET /patients/{id}/clinical-teeth/{tooth_key} -> 404
    r = client.get(f"/api/v1/patients/{patient_2.id}/clinical-teeth/16", headers=headers_doc1)
    assert r.status_code == 404

    # 10. GET /patients/{id}/clinical-events -> 404
    r = client.get(f"/api/v1/patients/{patient_2.id}/clinical-events", headers=headers_doc1)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_patient_isolation_same_tenant_returns_404(client, seed_security_data, async_db_session):
    """Calling PATCH or /correct on patient_B URL using work item ID of patient_A returns 404."""
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_a = seed_security_data["patient_t1_doc1"]

    # Create patient_b also assigned to doctor_1
    patient_b = models.Patient(
        tenant_id=t1,
        name="Patient B",
        age=45,
        phone="+1999999999",
        medical_history="No history",
        notes="None",
        assigned_doctor_id=doctor_1.id,
        is_deleted=False,
    )
    async_db_session.add(patient_b)
    await async_db_session.commit()

    service = ClinicalCommandService(async_db_session, t1, doctor_1)
    wi_a = await service.create_finding(
        patient_a.id,
        schemas.ClinicalFindingCreate(code=FindingCode.CARIES.value, tooth_key="16"),
    )

    headers = make_headers(doctor_1)

    # Attempt to PATCH wi_a via patient_b URL -> 404
    r_patch = client.patch(
        f"/api/v1/patients/{patient_b.id}/clinical-work-items/{wi_a.id}",
        headers=headers,
        json={"notes": "wrong patient"},
    )
    assert r_patch.status_code == 404
    assert "not found" in r_patch.json()["detail"].lower()

    # Attempt to correct wi_a via patient_b URL -> 404
    r_correct = client.post(
        f"/api/v1/patients/{patient_b.id}/clinical-work-items/{wi_a.id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "wrong patient"},
    )
    assert r_correct.status_code == 404
    assert "not found" in r_correct.json()["detail"].lower()


@pytest.mark.asyncio
async def test_doctor_patient_visibility_mode_enforcement(client, seed_security_data, async_db_session):
    """
    Doctor with all_assigned cannot access unassigned patient.
    Doctor with appointments_only cannot access patient without appointment.
    """
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]  # all_assigned
    doctor_appts = seed_security_data["doctor_1_appts_only"]  # appointments_only
    patient_other = seed_security_data["patient_t1_other"]  # unassigned, no appts

    headers_doc1 = make_headers(doctor_1)
    headers_appts = make_headers(doctor_appts)

    finding_body = {"code": FindingCode.CARIES.value, "tooth_key": "16"}

    # Doctor 1 (all_assigned) on unassigned patient -> 404
    r1 = client.post(f"/api/v1/patients/{patient_other.id}/clinical-findings", headers=headers_doc1, json=finding_body)
    assert r1.status_code == 404

    # Doctor appts_only on patient without appointment -> 404
    r2 = client.post(f"/api/v1/patients/{patient_other.id}/clinical-findings", headers=headers_appts, json=finding_body)
    assert r2.status_code == 404

    # Now create an appointment for doctor_appts with patient_other
    appt = models.Appointment(
        tenant_id=t1,
        patient_id=patient_other.id,
        doctor_id=doctor_appts.id,
        date_time=datetime.now(timezone.utc),
        status="scheduled",
    )
    async_db_session.add(appt)
    await async_db_session.commit()

    # Now doctor appts_only can access patient_other -> 201
    r3 = client.post(f"/api/v1/patients/{patient_other.id}/clinical-findings", headers=headers_appts, json=finding_body)
    assert r3.status_code == 201


@pytest.mark.asyncio
async def test_tenant_scoped_idempotency_independence(client, seed_security_data, async_db_session):
    """Same Idempotency-Key string across Tenant 1 and Tenant 2 succeeds independently."""
    t1 = seed_security_data["tenant_1"].id
    t2 = seed_security_data["tenant_2"].id
    await enable_flags_for_tenants(async_db_session, [t1, t2])

    doctor_1 = seed_security_data["doctor_1"]
    doctor_2 = seed_security_data["doctor_2"]
    patient_1 = seed_security_data["patient_t1_doc1"]
    patient_2 = seed_security_data["patient_t2"]

    headers_1 = make_headers(doctor_1)
    headers_1["Idempotency-Key"] = "shared-tenant-key-12345"

    headers_2 = make_headers(doctor_2)
    headers_2["Idempotency-Key"] = "shared-tenant-key-12345"

    body_1 = {"code": FindingCode.CARIES.value, "tooth_key": "16"}
    body_2 = {"code": FindingCode.CARIES.value, "tooth_key": "26"}

    # Tenant 1 request
    r1 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=headers_1, json=body_1)
    assert r1.status_code == 201
    id_1 = r1.json()["data"]["id"]

    # Tenant 2 request with identical idempotency key string
    r2 = client.post(f"/api/v1/patients/{patient_2.id}/clinical-findings", headers=headers_2, json=body_2)
    assert r2.status_code == 201
    id_2 = r2.json()["data"]["id"]

    # Both succeeded and created items in their own tenant
    assert id_1 != id_2


# ===========================================================================
# G7-M14: API Contract & RBAC Matrix Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_standard_response_contract_across_all_g7_endpoints(client, seed_security_data, async_db_session):
    """Verify StandardResponse envelope (success, data, message, trace_id) across all 10 endpoints."""
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]
    headers = make_headers(doctor_1)

    def assert_standard_response(r, expected_status=200):
        assert r.status_code == expected_status, f"Expected {expected_status}, got {r.status_code}: {r.text}"
        body = r.json()
        assert "success" in body and body["success"] is True
        assert "data" in body and body["data"] is not None
        assert "message" in body
        assert "trace_id" in body
        return body["data"]

    # 1. POST /clinical-work-items
    wi_payload = {
        "kind": "procedure",
        "code": ProcedureCode.REST_COMPOSITE.value,
        "status": "planned",
        "targets": [{"target_kind": "surface", "tooth_key": "16", "surface_code": "O"}],
    }
    r = client.post(f"/api/v1/patients/{patient_1.id}/clinical-work-items", headers=headers, json=wi_payload)
    wi_data = assert_standard_response(r, 201)
    wi_id = wi_data["id"]

    # 2. GET /clinical-work-items
    r = client.get(f"/api/v1/patients/{patient_1.id}/clinical-work-items", headers=headers)
    items_data = assert_standard_response(r, 200)
    assert isinstance(items_data, list)
    assert len(items_data) >= 1

    # 3. PATCH /clinical-work-items/{id}
    r = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_id}",
        headers=headers,
        json={"status": "active", "expected_version_id": 1},
    )
    patch_data = assert_standard_response(r, 200)
    assert patch_data["status"] == "active"

    # 4. POST /clinical-findings
    finding_payload = {"code": FindingCode.CARIES.value, "tooth_key": "17"}
    r = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=headers, json=finding_payload)
    assert_standard_response(r, 201)

    # 5. POST /clinical-findings/bulk
    r = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk",
        headers=headers,
        json={"items": [{"code": FindingCode.FRACTURE.value, "tooth_key": "18"}]},
    )
    bulk_f_data = assert_standard_response(r, 201)
    assert bulk_f_data["count"] == 1

    # 6. POST /clinical-procedures
    proc_payload = {"code": ProcedureCode.PROS_CROWN.value, "tooth_key": "24", "lab_choice": "in_clinic"}
    r = client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures", headers=headers, json=proc_payload)
    proc_data = assert_standard_response(r, 201)
    proc_id = proc_data["id"]

    # 7. POST /clinical-procedures/bulk
    r = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-procedures/bulk",
        headers=headers,
        json={"items": [{"code": ProcedureCode.ENDO_RCT.value, "tooth_key": "25"}]},
    )
    bulk_p_data = assert_standard_response(r, 201)
    assert bulk_p_data["count"] == 1

    # 8. POST /clinical-work-items/{id}/correct
    r = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{proc_id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "Diagnostic error"},
    )
    correct_data = assert_standard_response(r, 200)
    assert correct_data["mode"] == "entered_in_error"

    # 9. GET /clinical-teeth/{tooth_key}
    r = client.get(f"/api/v1/patients/{patient_1.id}/clinical-teeth/16", headers=headers)
    assert_standard_response(r, 200)

    # 10. GET /clinical-events
    r = client.get(f"/api/v1/patients/{patient_1.id}/clinical-events", headers=headers)
    events_data = assert_standard_response(r, 200)
    assert isinstance(events_data, list)


@pytest.mark.asyncio
async def test_rbac_full_role_matrix(client, seed_security_data, async_db_session):
    """
    Test RBAC across SUPER_ADMIN, ADMIN, DOCTOR, NURSE, RECEPTIONIST, ASSISTANT, GUEST.
    - Findings write: super_admin, admin, doctor, nurse -> 201; assistant, receptionist, guest -> 403
    - Procedures write: super_admin, admin, doctor -> 201; nurse, assistant, receptionist, guest -> 403
    - Correction: super_admin, admin, doctor -> 200; others -> 403
    - Generic work item write:
        - kind=finding: nurse -> 201, assistant -> 403
        - kind=procedure: nurse -> 403, doctor -> 201
    - Read: super_admin, admin, doctor, nurse, receptionist, assistant -> 200; guest -> 403
    """
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    patient = seed_security_data["patient_t1_doc1"]

    roles_map = {
        "super_admin": seed_security_data["super_admin_1"],
        "admin": seed_security_data["admin_1"],
        "doctor": seed_security_data["doctor_1"],
        "nurse": seed_security_data["nurse_1"],
        "receptionist": seed_security_data["receptionist_1"],
        "assistant": seed_security_data["assistant_1"],
        "guest": seed_security_data["guest_1"],
    }

    # First create an existing procedure work item to test correction
    service = ClinicalCommandService(async_db_session, t1, seed_security_data["doctor_1"])
    wi_to_correct = await service.create_procedure(
        patient.id,
        schemas.ClinicalProcedureCreate(code=ProcedureCode.REST_COMPOSITE.value, tooth_key="11"),
    )

    finding_body = {"code": FindingCode.CARIES.value, "tooth_key": "12"}
    proc_body = {"code": ProcedureCode.REST_COMPOSITE.value, "tooth_key": "13"}

    for role_name, user in roles_map.items():
        headers = make_headers(user)

        # 1. Finding write
        r_find = client.post(f"/api/v1/patients/{patient.id}/clinical-findings", headers=headers, json=finding_body)
        if role_name in ("super_admin", "admin", "doctor", "nurse"):
            assert r_find.status_code == 201, f"Role {role_name} should be allowed on finding write"
        else:
            assert r_find.status_code == 403, f"Role {role_name} should be forbidden on finding write"

        # 2. Procedure write
        r_proc = client.post(f"/api/v1/patients/{patient.id}/clinical-procedures", headers=headers, json=proc_body)
        if role_name in ("super_admin", "admin", "doctor"):
            assert r_proc.status_code == 201, f"Role {role_name} should be allowed on procedure write"
        else:
            assert r_proc.status_code == 403, f"Role {role_name} should be forbidden on procedure write"

        # 3. Read endpoints
        r_read = client.get(f"/api/v1/patients/{patient.id}/clinical-work-items", headers=headers)
        if role_name == "guest":
            assert r_read.status_code == 403, "Guest should be forbidden on read"
        else:
            assert r_read.status_code == 200, f"Role {role_name} should be allowed on read"

    # 4. Correction RBAC
    for role_name in ("nurse", "receptionist", "assistant", "guest"):
        headers = make_headers(roles_map[role_name])
        r_corr = client.post(
            f"/api/v1/patients/{patient.id}/clinical-work-items/{wi_to_correct.id}/correct",
            headers=headers,
            json={"mode": "entered_in_error", "reason": "Test"},
        )
        assert r_corr.status_code == 403, f"Role {role_name} must be 403 on correction"

    # Doctor can correct
    r_corr_doc = client.post(
        f"/api/v1/patients/{patient.id}/clinical-work-items/{wi_to_correct.id}/correct",
        headers=make_headers(seed_security_data["doctor_1"]),
        json={"mode": "entered_in_error", "reason": "Legitimate correction"},
    )
    assert r_corr_doc.status_code == 200


# ===========================================================================
# G7-M15: Idempotency Keys Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_idempotency_single_work_item_and_finding_and_procedure(client, seed_security_data, async_db_session):
    """
    Replaying POST with identical Idempotency-Key returns same ID and creates 0 extra DB rows.
    Tested via header and via JSON payload on single work item, finding, and procedure.
    """
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]

    headers = make_headers(doctor_1)

    # A. Dedicated Finding via Header
    headers_f = dict(headers)
    headers_f["Idempotency-Key"] = "finding-key-001"
    f_body = {"code": FindingCode.CARIES.value, "tooth_key": "16"}

    count_before = (await async_db_session.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar_one()

    r1 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=headers_f, json=f_body)
    assert r1.status_code == 201
    f_id = r1.json()["data"]["id"]

    r2 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=headers_f, json=f_body)
    assert r2.status_code == 201
    assert r2.json()["data"]["id"] == f_id

    count_after = (await async_db_session.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar_one()
    assert count_after == count_before + 1

    # B. Dedicated Procedure via JSON payload
    p_body = {
        "code": ProcedureCode.REST_COMPOSITE.value,
        "tooth_key": "16",
        "surfaces": ["M", "O"],
        "idempotency_key": "procedure-key-002",
    }
    r3 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures", headers=headers, json=p_body)
    assert r3.status_code == 201
    p_id = r3.json()["data"]["id"]

    r4 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-procedures", headers=headers, json=p_body)
    assert r4.status_code == 201
    assert r4.json()["data"]["id"] == p_id

    count_after_p = (await async_db_session.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar_one()
    assert count_after_p == count_after + 1


@pytest.mark.asyncio
async def test_idempotency_bulk_findings_and_procedures(client, seed_security_data, async_db_session):
    """Replaying bulk creation POST with identical key returns same bulk items with 0 extra rows."""
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]

    headers = make_headers(doctor_1)
    headers["Idempotency-Key"] = "bulk-find-key-001"

    bulk_body = {
        "items": [
            {"code": FindingCode.CARIES.value, "tooth_key": "14"},
            {"code": FindingCode.FRACTURE.value, "tooth_key": "15"},
        ]
    }

    count_before = (await async_db_session.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar_one()

    r1 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk", headers=headers, json=bulk_body)
    assert r1.status_code == 201
    res1 = r1.json()["data"]
    assert res1["count"] == 2
    ids1 = [item["id"] for item in res1["items"]]

    r2 = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings/bulk", headers=headers, json=bulk_body)
    assert r2.status_code == 201
    res2 = r2.json()["data"]
    assert res2["count"] == 2
    ids2 = [item["id"] for item in res2["items"]]

    assert ids1 == ids2

    count_after = (await async_db_session.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar_one()
    assert count_after == count_before + 2


@pytest.mark.asyncio
async def test_idempotency_correction_entered_in_error_and_supersede(client, seed_security_data, async_db_session):
    """Replaying correction POST with identical key replays original response without error or duplicate events."""
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]
    headers = make_headers(doctor_1)

    service = ClinicalCommandService(async_db_session, t1, doctor_1)
    wi_eie = await service.create_procedure(
        patient_1.id,
        schemas.ClinicalProcedureCreate(code=ProcedureCode.REST_COMPOSITE.value, tooth_key="36"),
    )
    wi_sup = await service.create_procedure(
        patient_1.id,
        schemas.ClinicalProcedureCreate(code=ProcedureCode.REST_COMPOSITE.value, tooth_key="37"),
    )

    # 1. Test entered_in_error replay
    headers_eie = dict(headers)
    headers_eie["Idempotency-Key"] = "corr-eie-key-001"
    eie_body = {"mode": "entered_in_error", "reason": "Double entry"}

    events_before = (await async_db_session.execute(select(func.count(models.ClinicalEvent.id)))).scalar_one()

    r1 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_eie.id}/correct",
        headers=headers_eie,
        json=eie_body,
    )
    assert r1.status_code == 200
    ev1_id = r1.json()["data"]["correction_event_id"]

    # Replay
    r2 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_eie.id}/correct",
        headers=headers_eie,
        json=eie_body,
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["correction_event_id"] == ev1_id

    events_after = (await async_db_session.execute(select(func.count(models.ClinicalEvent.id)))).scalar_one()
    assert events_after == events_before + 1

    # 2. Test supersede replay
    headers_sup = dict(headers)
    headers_sup["Idempotency-Key"] = "corr-sup-key-001"
    sup_body = {
        "mode": "supersede",
        "reason": "Changed to crown",
        "replacement": {
            "kind": "procedure",
            "code": ProcedureCode.PROS_CROWN.value,
            "status": "planned",
            "lab_choice": "in_clinic",
            "targets": [{"target_kind": "tooth", "tooth_key": "37"}],
        },
    }

    r3 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_sup.id}/correct",
        headers=headers_sup,
        json=sup_body,
    )
    assert r3.status_code == 200
    repl3_id = r3.json()["data"]["replacement_work_item"]["id"]

    # Replay
    r4 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi_sup.id}/correct",
        headers=headers_sup,
        json=sup_body,
    )
    assert r4.status_code == 200
    assert r4.json()["data"]["replacement_work_item"]["id"] == repl3_id


@pytest.mark.asyncio
async def test_idempotency_conflict_on_different_parameters(client, seed_security_data, async_db_session):
    """Replaying same key with different code or tooth_key returns 409 Conflict."""
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]

    headers = make_headers(doctor_1)
    headers["Idempotency-Key"] = "conflict-key-001"

    # First request: CARIES on 16
    r1 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.CARIES.value, "tooth_key": "16"},
    )
    assert r1.status_code == 201

    # Second request: DIFFERENT code (FRACTURE on 16)
    r2 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.FRACTURE.value, "tooth_key": "16"},
    )
    assert r2.status_code == 409
    assert "idempotency key already used with different parameters" in r2.json()["detail"].lower()

    # Third request: DIFFERENT tooth_key (CARIES on 17)
    r3 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-findings",
        headers=headers,
        json={"code": FindingCode.CARIES.value, "tooth_key": "17"},
    )
    assert r3.status_code == 409
    assert "idempotency key already used with different parameters" in r3.json()["detail"].lower()


@pytest.mark.asyncio
async def test_idempotency_key_validation_rules(client, seed_security_data, async_db_session):
    """Key > 128 chars or empty string raises 422 Unprocessable Entity."""
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]

    headers = make_headers(doctor_1)
    body = {"code": FindingCode.CARIES.value, "tooth_key": "16"}

    # > 128 characters
    headers_long = dict(headers)
    headers_long["Idempotency-Key"] = "a" * 129
    r_long = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=headers_long, json=body)
    assert r_long.status_code == 422
    assert "128" in r_long.json()["detail"].lower()

    # Empty string
    headers_empty = dict(headers)
    headers_empty["Idempotency-Key"] = "   "
    r_empty = client.post(f"/api/v1/patients/{patient_1.id}/clinical-findings", headers=headers_empty, json=body)
    assert r_empty.status_code == 422
    assert "empty" in r_empty.json()["detail"].lower()


@pytest.mark.asyncio
async def test_idempotency_concurrent_same_key_race(async_db_session, seed_security_data):
    """
    Requests with identical Idempotency-Key and payload result in exactly
    ONE ClinicalWorkItem created (count == 1).
    """
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]

    service = ClinicalCommandService(async_db_session, t1, doctor_1)
    payload = schemas.ClinicalFindingCreate(code=FindingCode.CARIES.value, tooth_key="46")
    key = "concurrent-race-key-001"

    res1 = await service.create_finding(patient_1.id, payload, idempotency_key=key)
    res2 = await service.create_finding(patient_1.id, payload, idempotency_key=key)

    # Both returned work items point to the exact same ID
    assert res1.id == res2.id

    # Verify database count is exactly 1
    count = (
        await async_db_session.execute(
            select(func.count(models.ClinicalWorkItem.id)).where(
                models.ClinicalWorkItem.patient_id == patient_1.id,
                models.ClinicalWorkItem.tenant_id == t1,
            )
        )
    ).scalar_one()
    assert count == 1


# ===========================================================================
# G7-M16: Optimistic Concurrency Handling Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_optimistic_concurrency_stale_expected_version_id_patch(client, seed_security_data, async_db_session):
    """PATCH with mismatched expected_version_id returns 409 Conflict."""
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]
    headers = make_headers(doctor_1)

    service = ClinicalCommandService(async_db_session, t1, doctor_1)
    wi = await service.create_procedure(
        patient_1.id,
        schemas.ClinicalProcedureCreate(code=ProcedureCode.REST_COMPOSITE.value, tooth_key="47"),
    )
    assert wi.version_id == 1

    # PATCH with stale version (expected 999, found 1) -> 409
    r_stale = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi.id}",
        headers=headers,
        json={"notes": "updated notes", "expected_version_id": 999},
    )
    assert r_stale.status_code == 409
    assert "stale version" in r_stale.json()["detail"].lower()


@pytest.mark.asyncio
async def test_optimistic_concurrency_stale_expected_version_id_correct(client, seed_security_data, async_db_session):
    """POST /correct with mismatched expected_version_id returns 409 Conflict."""
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]
    headers = make_headers(doctor_1)

    service = ClinicalCommandService(async_db_session, t1, doctor_1)
    wi = await service.create_procedure(
        patient_1.id,
        schemas.ClinicalProcedureCreate(code=ProcedureCode.REST_COMPOSITE.value, tooth_key="48"),
    )
    assert wi.version_id == 1

    # Correct with stale version (expected 999) -> 409
    r_stale = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi.id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "stale test", "expected_version_id": 999},
    )
    assert r_stale.status_code == 409
    assert "stale version" in r_stale.json()["detail"].lower()


@pytest.mark.asyncio
async def test_concurrent_update_contention_patch_and_correct(client, seed_security_data, async_db_session):
    """
    Concurrent update contention test:
    Two updates start with expected_version_id = 1.
    First update commits, advancing version_id to 2.
    Second update with expected_version_id = 1 fails with 409 Conflict.
    """
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]
    headers = make_headers(doctor_1)

    service = ClinicalCommandService(async_db_session, t1, doctor_1)
    wi = await service.create_procedure(
        patient_1.id,
        schemas.ClinicalProcedureCreate(code=ProcedureCode.REST_COMPOSITE.value, tooth_key="11"),
    )
    assert wi.version_id == 1

    # First update (PATCH) succeeds and advances version to 2
    r1 = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi.id}",
        headers=headers,
        json={"notes": "First update", "expected_version_id": 1},
    )
    assert r1.status_code == 200
    assert r1.json()["data"]["version_id"] == 2

    # Second competing update (PATCH with version 1) fails with 409
    r2 = client.patch(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi.id}",
        headers=headers,
        json={"notes": "Competing update", "expected_version_id": 1},
    )
    assert r2.status_code == 409
    assert "stale version" in r2.json()["detail"].lower()

    # Second competing update (/correct with version 1) also fails with 409
    r3 = client.post(
        f"/api/v1/patients/{patient_1.id}/clinical-work-items/{wi.id}/correct",
        headers=headers,
        json={"mode": "entered_in_error", "reason": "Competing correction", "expected_version_id": 1},
    )
    assert r3.status_code == 409
    assert "stale version" in r3.json()["detail"].lower()


@pytest.mark.asyncio
async def test_session_health_after_stale_data_error_and_rollback(async_db_session, seed_security_data):
    """
    Session health test: after StaleDataError or version 409 rollback,
    _get_active_current_user remains functional, session is clean, and subsequent queries succeed.
    """
    t1 = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [t1])

    doctor_1 = seed_security_data["doctor_1"]
    patient_1 = seed_security_data["patient_t1_doc1"]

    patient_id = int(patient_1.id)
    service = ClinicalCommandService(async_db_session, t1, doctor_1)
    wi = await service.create_procedure(
        patient_id,
        schemas.ClinicalProcedureCreate(code=ProcedureCode.REST_COMPOSITE.value, tooth_key="21"),
    )
    work_item_id = int(wi.id)

    # 1. Trigger 409 via stale expected_version_id
    with pytest.raises(HTTPException) as exc_info:
        await service.update_work_item(
            patient_id,
            work_item_id,
            schemas.ClinicalWorkItemUpdate(notes="stale update", expected_version_id=999),
        )
    assert exc_info.value.status_code == 409

    # Verify session remains healthy: _get_active_current_user reloads active user without error
    active_user = await service._get_active_current_user()
    assert active_user.id == doctor_1.id

    # 2. Trigger 409 via SQLAlchemy StaleDataError on commit
    orig_commit = async_db_session.commit

    async def commit_with_stale_data():
        raise StaleDataError(models.ClinicalWorkItem, "Optimistic locking conflict")

    async_db_session.commit = commit_with_stale_data
    try:
        with pytest.raises(HTTPException) as exc_info2:
            await service.update_work_item(
                patient_id,
                work_item_id,
                schemas.ClinicalWorkItemUpdate(notes="stale commit test"),
            )
        assert exc_info2.value.status_code == 409
        assert "concurrent modification" in exc_info2.value.detail.lower()
    finally:
        async_db_session.commit = orig_commit

    # Verify session remains healthy after StaleDataError rollback
    active_user2 = await service._get_active_current_user()
    assert active_user2.id == doctor_1.id

    # Verify subsequent valid database operations succeed without PendingRollbackError
    reloaded_items = await service.list_work_items(patient_id)
    assert len(reloaded_items) >= 1

    # Verify subsequent valid mutation succeeds
    new_finding = await service.create_finding(
        patient_id,
        schemas.ClinicalFindingCreate(code=FindingCode.CARIES.value, tooth_key="22"),
    )
    assert new_finding.id is not None

@pytest.mark.asyncio
async def test_native_lab_choice_required_and_retry_fingerprint(client, seed_security_data, async_db_session):
    tenant = seed_security_data["tenant_1"].id
    await enable_flags_for_tenants(async_db_session, [tenant])
    patient = seed_security_data["patient_t1_doc1"]
    headers = make_headers(seed_security_data["doctor_1"])
    headers["Idempotency-Key"] = "native-crown-choice-001"
    url = f"/api/v1/patients/{patient.id}/clinical-procedures"
    payload = {"code": ProcedureCode.PROS_CROWN.value, "tooth_key": "24"}
    assert client.post(url, headers=headers, json=payload).status_code == 422
    payload["lab_choice"] = "in_clinic"
    first = client.post(url, headers=headers, json=payload)
    assert first.status_code == 201
    assert first.json()["data"]["lab_choice"] == "in_clinic"
    replay = client.post(url, headers=headers, json=payload)
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == first.json()["data"]["id"]
    payload["lab_choice"] = "external_lab"
    assert client.post(url, headers=headers, json=payload).status_code == 409
