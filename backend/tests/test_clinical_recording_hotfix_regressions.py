"""
Release-sensitive regression tests for the five clinical recording QA hotfix findings:
1. Active-session Add Procedure HTTP behavior (valid 201 + structured 422 + RBAC/visibility).
3b. POST /finish with next_visit_request (MissingGreenlet 500 regression + related read paths).
4. POST /treatments/tooth_status with Missing (persists Missing, not Extracted, 0 treatments,
   native/legacy workspace snapshot compatibility including COMPLETE coverage).
5. Quick Actions native proposed ClinicalWorkItem visibility via GET clinical-work-items
   without altering /treatments or creating synthetic billable treatments.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from backend import models
from backend.auth import create_access_token
from backend.main import app
from backend.services.clinical_workspace_service import (
    FEATURE_FLAG_CLINICAL_PRIMARY,
    ClinicalWorkspaceService,
)
from backend.services.feature_service import FeatureFlagService
from backend.tests.services.test_care_session_workflow_unification_v2 import (
    seed_visit,
    setup_env as setup_env,
)


def _auth_headers(user: models.User) -> dict[str, str]:
    token = create_access_token(
        data={"sub": user.username, "tenant_id": user.tenant_id, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_add_second_procedure_returns_201_and_invalid_id_returns_structured_422(
    async_db_session, setup_env
):
    """Finding 1: Adding a valid second procedure succeeds (201); invalid path param returns structured 422."""
    env = setup_env
    session, first_item, _ = await seed_visit(async_db_session, env, status="in_progress")

    second_item = models.ClinicalWorkItem(
        tenant_id=env["tenant"].id,
        patient_id=env["patient1"].id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
        created_by_user_id=env["doctor1"].id,
    )
    async_db_session.add(second_item)
    await async_db_session.flush()
    async_db_session.add(
        models.ClinicalWorkItemTarget(
            tenant_id=env["tenant"].id,
            work_item_id=second_item.id,
            target_kind="tooth",
            tooth_key="21",
        )
    )
    reception = models.User(
        tenant_id=env["tenant"].id,
        username="hotfix_reception_addproc",
        hashed_password="synthetic",
        role="receptionist",
        is_active=True,
    )
    async_db_session.add(reception)
    await async_db_session.commit()

    doc1_headers = _auth_headers(env["doctor1"])
    doc2_headers = _auth_headers(env["doctor2"])
    reception_headers = _auth_headers(reception)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Valid second procedure -> 201
        ok_resp = await client.post(
            f"/api/v1/patients/{env['patient1'].id}/care-sessions/{session.id}/procedures/{second_item.id}",
            headers=doc1_headers,
        )
        assert ok_resp.status_code == 201, ok_resp.text
        assert ok_resp.json()["data"]["work_item_id"] == second_item.id

        # Invalid work_item_id -> structured 422 array detail
        bad_resp = await client.post(
            f"/api/v1/patients/{env['patient1'].id}/care-sessions/{session.id}/procedures/not-an-int",
            headers=doc1_headers,
        )
        assert bad_resp.status_code == 422
        detail = bad_resp.json()["detail"]
        assert isinstance(detail, list) and len(detail) > 0
        assert isinstance(detail[0], dict) and "msg" in detail[0]

        # RBAC & visibility boundaries preserved
        rec_resp = await client.post(
            f"/api/v1/patients/{env['patient1'].id}/care-sessions/{session.id}/procedures/{first_item.id}",
            headers=reception_headers,
        )
        assert rec_resp.status_code == 403

        hidden_resp = await client.post(
            f"/api/v1/patients/{env['patient1'].id}/care-sessions/{session.id}/procedures/{first_item.id}",
            headers=doc2_headers,
        )
        assert hidden_resp.status_code == 404


@pytest.mark.asyncio
async def test_finish_session_with_two_procedures_draft_and_next_visit_request_returns_200(
    async_db_session, setup_env
):
    """Finding 3b: POST /finish with next_visit_request must return 200 (not 500 MissingGreenlet)."""
    env = setup_env
    session, first_item, _ = await seed_visit(async_db_session, env, status="in_progress")

    second_item = models.ClinicalWorkItem(
        tenant_id=env["tenant"].id,
        patient_id=env["patient1"].id,
        kind="procedure",
        code="PROS_CROWN",
        status="active",
        created_by_user_id=env["doctor1"].id,
    )
    async_db_session.add(second_item)
    await async_db_session.flush()
    async_db_session.add(
        models.ClinicalWorkItemTarget(
            tenant_id=env["tenant"].id,
            work_item_id=second_item.id,
            target_kind="tooth",
            tooth_key="21",
        )
    )
    await async_db_session.commit()

    doc1_headers = _auth_headers(env["doctor1"])
    patient_id = env["patient1"].id

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # 1. Associate second procedure
        add_resp = await client.post(
            f"/api/v1/patients/{patient_id}/care-sessions/{session.id}/procedures/{second_item.id}",
            headers=doc1_headers,
        )
        assert add_resp.status_code == 201, add_resp.text

        # 2. Save server draft with procedure notes and next action
        draft_resp = await client.put(
            f"/api/v1/patients/{patient_id}/care-sessions/draft",
            headers=doc1_headers,
            json={
                "care_session_id": session.id,
                "expected_version_id": 1,
                "draft_data": {
                    f"proc_notes_{first_item.id}": "Access and instrumentation done",
                    f"proc_next_action_{first_item.id}": "Master cone fit",
                    f"proc_notes_{second_item.id}": "Crown prep completed",
                    f"proc_next_action_{second_item.id}": "Try-in crown",
                },
            },
        )
        assert draft_resp.status_code == 200, draft_resp.text

        # 3. Finish session WITH next_visit_request (previously committed then crashed with 500)
        finish_resp = await client.post(
            f"/api/v1/patients/{patient_id}/care-sessions/{session.id}/finish",
            headers=doc1_headers,
            json={
                "notes": "Patient tolerated procedure well",
                "next_visit_request": {
                    "care_session_id": session.id,
                    "work_item_id": second_item.id,
                    "associated_work_item_ids": [first_item.id, second_item.id],
                    "reason": "Tooth 21: Crown Try-In",
                    "suggested_duration_minutes": 45,
                    "notes": "Schedule in 7 days",
                },
            },
        )
        assert finish_resp.status_code == 200, finish_resp.text
        finished_data = finish_resp.json()["data"]
        assert finished_data["status"] == "completed"
        assert len(finished_data["next_visit_requests"]) == 1
        nvr = finished_data["next_visit_requests"][0]
        assert nvr["reason"] == "Tooth 21: Crown Try-In"
        assert nvr["work_item_id"] == second_item.id
        # No broadened PII on session-scoped finish response when patient relation wasn't requested
        assert nvr["patient_phone"] is None

        proc_by_wi = {p["work_item_id"]: p for p in finished_data["procedures"]}
        assert proc_by_wi[first_item.id]["procedure_notes"] == "Access and instrumentation done"
        assert proc_by_wi[first_item.id]["next_action"] == "Master cone fit"
        assert proc_by_wi[second_item.id]["procedure_notes"] == "Crown prep completed"
        assert proc_by_wi[second_item.id]["next_action"] == "Try-in crown"

        # 4. Verify related read/write endpoints sharing NextVisitRequestRead also succeed without MissingGreenlet
        get_sess_resp = await client.get(
            f"/api/v1/patients/{patient_id}/care-sessions/{session.id}",
            headers=doc1_headers,
        )
        assert get_sess_resp.status_code == 200, get_sess_resp.text
        assert len(get_sess_resp.json()["data"]["next_visit_requests"]) == 1

        list_sess_resp = await client.get(
            f"/api/v1/patients/{patient_id}/care-sessions",
            headers=doc1_headers,
        )
        assert list_sess_resp.status_code == 200, list_sess_resp.text

        list_nvr_resp = await client.get(
            f"/api/v1/patients/{patient_id}/next-visit-requests",
            headers=doc1_headers,
        )
        assert list_nvr_resp.status_code == 200, list_nvr_resp.text
        assert len(list_nvr_resp.json()["data"]) == 1

        # Create standalone next-visit request -> 201
        create_nvr_resp = await client.post(
            f"/api/v1/patients/{patient_id}/next-visit-requests",
            headers=doc1_headers,
            json={
                "reason": "Follow-up sensitivity check",
                "suggested_duration_minutes": 15,
            },
        )
        assert create_nvr_resp.status_code == 201, create_nvr_resp.text
        created_nvr_id = create_nvr_resp.json()["data"]["id"]

        # Reception queue still enriches patient_name/patient_phone and respects visibility
        queue_resp = await client.get("/api/v1/next-visit-requests", headers=doc1_headers)
        assert queue_resp.status_code == 200, queue_resp.text
        queue_items = queue_resp.json()["data"]
        assert len(queue_items) == 2
        assert all(item["patient_id"] == patient_id for item in queue_items)
        assert all(item["patient_name"] == env["patient1"].name for item in queue_items)

        # Lifecycle mutation on next-visit request still returns 200 cleanly
        postpone_dt = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        postpone_resp = await client.post(
            f"/api/v1/patients/{patient_id}/next-visit-requests/{created_nvr_id}/postpone",
            headers=doc1_headers,
            json={"postponed_to_date": postpone_dt, "reason": "Patient traveling"},
        )
        assert postpone_resp.status_code == 200, postpone_resp.text
        assert postpone_resp.json()["data"]["status"] == "postponed"


@pytest.mark.asyncio
async def test_tooth_status_missing_persists_without_treatments_and_projects_in_native_complete_coverage(
    async_db_session, setup_env
):
    """Finding 4: POST /treatments/tooth_status persists Missing (not Extracted), creates 0 treatments,
    and projects cleanly in both legacy/uncovered and VNEXT_PRIMARY COMPLETE coverage."""
    env = setup_env
    patient_id = env["patient1"].id

    # Enable VNEXT_PRIMARY and mark teeth coverage COMPLETE to exercise strict native snapshot coverage
    flag_primary = (
        await async_db_session.execute(
            select(models.FeatureFlag).where(
                models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_PRIMARY
            )
        )
    ).scalar_one_or_none()
    if not flag_primary:
        flag_primary = models.FeatureFlag(
            key=FEATURE_FLAG_CLINICAL_PRIMARY,
            description="Primary workspace",
            is_global_enabled=True,
            rollout_percentage=0,
        )
        async_db_session.add(flag_primary)
        await async_db_session.flush()
    await FeatureFlagService.set_tenant_override(
        async_db_session, env["tenant"].id, FEATURE_FLAG_CLINICAL_PRIMARY, True
    )
    async_db_session.add(
        models.ClinicalProjectionCoverage(
            tenant_id=env["tenant"].id,
            patient_id=patient_id,
            domain="teeth",
            status="COMPLETE",
        )
    )
    await async_db_session.commit()

    doc1_headers = _auth_headers(env["doctor1"])
    doc2_headers = _auth_headers(env["doctor2"])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Hidden doctor rejected
        hidden_resp = await client.post(
            "/api/v1/treatments/tooth_status",
            headers=doc2_headers,
            json={"patient_id": patient_id, "tooth_number": 16, "condition": "Missing"},
        )
        assert hidden_resp.status_code == 404

        # Authorized doctor marks tooth 16 as Missing
        resp = await client.post(
            "/api/v1/treatments/tooth_status",
            headers=doc1_headers,
            json={"patient_id": patient_id, "tooth_number": 16, "condition": "Missing"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["condition"] == "Missing"

        # Legacy read reflects Missing
        ts_resp = await client.get(
            f"/api/v1/patients/{patient_id}/tooth_status", headers=doc1_headers
        )
        assert ts_resp.status_code == 200
        tooth_16_rows = [r for r in ts_resp.json()["data"] if r["tooth_number"] == 16]
        assert len(tooth_16_rows) == 1
        assert tooth_16_rows[0]["condition"] == "Missing"

        # Workspace snapshot reflects MISSING (NOT EXTRACTED) even under COMPLETE teeth coverage
        ws_resp = await client.get(
            f"/api/v1/patients/{patient_id}/clinical-workspace", headers=doc1_headers
        )
        assert ws_resp.status_code == 200, ws_resp.text
        ws_tooth_16 = ws_resp.json()["data"]["teeth"]["16"]
        assert ws_tooth_16["lifecycle"] == "MISSING"
        assert ws_tooth_16["condition"] == "Missing"

        # Zero synthetic treatments created
        treatments_count = await async_db_session.scalar(
            select(func.count(models.Treatment.id)).where(
                models.Treatment.tenant_id == env["tenant"].id,
                models.Treatment.patient_id == patient_id,
            )
        )
        assert treatments_count == 0


@pytest.mark.asyncio
async def test_quick_action_proposed_procedure_available_in_clinical_work_items_without_mutating_treatments(
    async_db_session, setup_env
):
    """Finding 5: Native Quick Action creates a proposed ClinicalWorkItem readable from
    GET /clinical-work-items while leaving /treatments unchanged (zero synthetic billable rows)."""
    env = setup_env
    patient_id = env["patient1"].id
    doc1_headers = _auth_headers(env["doctor1"])

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        create_resp = await client.post(
            f"/api/v1/patients/{patient_id}/clinical-procedures",
            headers=doc1_headers,
            json={
                "code": "SURG_EXTRACTION",
                "targets": [{"target_kind": "tooth", "tooth_key": "46"}],
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        created = create_resp.json()["data"]
        assert created["status"] == "proposed"
        assert created["kind"] == "procedure"

        wi_resp = await client.get(
            f"/api/v1/patients/{patient_id}/clinical-work-items",
            headers=doc1_headers,
        )
        assert wi_resp.status_code == 200, wi_resp.text
        work_items = wi_resp.json()["data"]
        assert any(
            w["id"] == created["id"] and w["status"] == "proposed" and w["code"] == "SURG_EXTRACTION"
            for w in work_items
        )

        # /treatments contract remains untouched with zero synthetic rows
        tr_resp = await client.get(
            f"/api/v1/patients/{patient_id}/treatments",
            headers=doc1_headers,
        )
        assert tr_resp.status_code == 200, tr_resp.text
        assert tr_resp.json()["data"] == []
