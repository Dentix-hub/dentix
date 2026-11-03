"""
Regression tests for PR-01 Task 07: Stale AI Session and Context Paths.

Verifies:
- Patient selected into AI session is revalidated on subsequent requests.
- When canonical visibility changes (patient reassigned / no longer visible),
  the next AI request clears the stale context and does not act on or leak it.
- Stale patient context is not sent to the LLM provider.
- Legitimate session context works.
- Tenant and user session separation remains intact.
"""

import pytest
from unittest.mock import patch, AsyncMock
from backend import models
from backend.auth import create_access_token, get_password_hash
from backend.ai.agent.state_manager import state_manager
from backend.services.ai_service import AIService
from backend.utils.patient_search_normalization import (
    normalize_patient_name_for_search,
    patient_phone_search_hash,
)


@pytest.fixture
def session_fixture(db_session):
    tenant1 = models.Tenant(name="Session Clinic 1", is_active=True)
    tenant2 = models.Tenant(name="Session Clinic 2", is_active=True)
    db_session.add_all([tenant1, tenant2])
    db_session.commit()
    for t in (tenant1, tenant2):
        db_session.refresh(t)

    doc1 = models.User(
        username="doc_sess_1",
        email="doc_sess_1@test.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant1.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    doc2 = models.User(
        username="doc_sess_2",
        email="doc_sess_2@test.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant1.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    doc_t2 = models.User(
        username="doc_sess_t2",
        email="doc_sess_t2@test.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant2.id,
        patient_visibility_mode="all_assigned",
        is_active=True,
    )
    db_session.add_all([doc1, doc2, doc_t2])
    db_session.commit()
    for u in (doc1, doc2, doc_t2):
        db_session.refresh(u)

    # Patient initially assigned to doc1
    patient = models.Patient(
        tenant_id=tenant1.id,
        name="Dynamic Visibility Patient",
        name_search_normalized=normalize_patient_name_for_search("Dynamic Visibility Patient"),
        phone="01111111111",
        phone_search_hash=patient_phone_search_hash("01111111111"),
        age=28,
        medical_history="None",
        notes="Original notes",
        assigned_doctor_id=doc1.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    return {
        "tenant1": tenant1,
        "tenant2": tenant2,
        "doc1": doc1,
        "doc2": doc2,
        "doc_t2": doc_t2,
        "patient": patient,
    }


def _auth_header(user):
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_stale_session_patient_cleared_when_visibility_revoked(async_db_session, session_fixture):
    """
    1. Patient is initially assigned to Doc 1 -> visible.
    2. Doc 1 has active_patient_id / active_patient_name in session.
    3. Patient is reassigned to Doc 2 (canonical visibility revoked from Doc 1).
    4. Next AI request by Doc 1 clears the stale patient and rejects confirmation / prompt enrichment.
    """
    doc1 = session_fixture["doc1"]
    doc2 = session_fixture["doc2"]
    patient = session_fixture["patient"]
    tenant_id = session_fixture["tenant1"].id

    # Step 1 & 2: Seed session state for Doc 1
    state_manager.update_session(
        tenant_id,
        doc1.id,
        {
            "active_patient_id": patient.id,
            "active_patient_name": patient.name,
            "pending_confirmation": {
                "tool": "record_medical_note",
                "params": {"patient_name": patient.name, "content": "Stale note"},
            },
        },
    )

    # Step 3: Canonical visibility changes (patient reassigned to Doc 2)
    p_async = await async_db_session.get(models.Patient, patient.id)
    p_async.assigned_doctor_id = doc2.id
    async_db_session.add(p_async)
    await async_db_session.commit()
    await async_db_session.refresh(p_async)

    # Step 4: Doc 1 confirms pending action
    service = AIService(async_db_session, doc1)
    with patch.object(service.agent, "_call_llm_safe", new_callable=AsyncMock) as mock_llm:
        # User says "نعم" to confirm
        response = await service.process_query(text="نعم")
        assert response.success is False
        assert "صلاحية" in response.message

        # LLM provider must NOT be called for revoked pending action
        mock_llm.assert_not_called()

        # Stale action must NOT execute on revoked patient
        await async_db_session.refresh(p_async)
        assert "Stale note" not in (p_async.notes or "")

        # Session must be cleared
        cleared_session = state_manager.get_session(tenant_id, doc1.id)
        assert cleared_session.active_patient_id is None
        assert cleared_session.active_patient_name is None
        assert cleared_session.pending_confirmation is None

        # Step 5: Verify prompt boundary on subsequent query with stale last_patient_name
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = '{"tool": "response", "message": "لا يوجد مريض محدد"}'
        mock_llm.return_value = mock_resp

        await service.process_query(text="ما هي المواعيد؟", last_patient_name=patient.name)

        # Provider was called, but revoked patient name must NOT be present in prompt messages
        mock_llm.assert_called_once()
        called_args, called_kwargs = mock_llm.call_args
        sent_messages = called_args[1] if len(called_args) > 1 else called_kwargs.get("messages", [])
        for msg in sent_messages:
            assert patient.name not in msg.get("content", "")


def test_stale_session_not_leaked_in_autocomplete_suggestions(client, session_fixture, db_session):
    """
    If session patient is reassigned, /ai/autocomplete must not suggest actions for that patient.
    """
    doc1 = session_fixture["doc1"]
    doc2 = session_fixture["doc2"]
    patient = session_fixture["patient"]
    tenant_id = session_fixture["tenant1"].id

    state_manager.update_session(
        tenant_id,
        doc1.id,
        {
            "active_patient_id": patient.id,
            "active_patient_name": patient.name,
        },
    )

    # Reassign patient to Doc 2
    patient.assigned_doctor_id = doc2.id
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    headers = _auth_header(doc1)
    res = client.get("/api/v1/ai/autocomplete?q=xyz", headers=headers)
    assert res.status_code == 200
    suggestions = res.json().get("suggestions", [])
    # No suggestion should reference the revoked patient
    for s in suggestions:
        assert patient.name not in s.get("text", "")


def test_session_isolation_across_users_and_tenants(session_fixture):
    """
    Ensure state_manager isolates keys across users and tenants.
    """
    t1 = session_fixture["tenant1"].id
    t2 = session_fixture["tenant2"].id
    u1 = session_fixture["doc1"].id
    u2 = session_fixture["doc2"].id
    u3 = session_fixture["doc_t2"].id

    state_manager.update_session(t1, u1, {"active_patient_id": 100})
    state_manager.update_session(t1, u2, {"active_patient_id": 200})
    state_manager.update_session(t2, u3, {"active_patient_id": 300})

    assert state_manager.get_session(t1, u1).active_patient_id == 100
    assert state_manager.get_session(t1, u2).active_patient_id == 200
    assert state_manager.get_session(t2, u3).active_patient_id == 300


@pytest.mark.asyncio
async def test_authorized_doctor_can_confirm_new_patient(async_db_session, session_fixture):
    """
    Confirming create_patient must succeed for an authorized doctor even though
    the new patient does not yet exist in the database.
    """
    doc1 = session_fixture["doc1"]
    tenant_id = session_fixture["tenant1"].id

    state_manager.update_session(
        tenant_id,
        doc1.id,
        {
            "active_patient_id": None,
            "active_patient_name": None,
            "pending_confirmation": {
                "tool": "create_patient",
                "params": {
                    "patient_name": "New Confirmed Patient",
                    "phone": "01077777777",
                    "age": 29,
                },
            },
        },
    )

    service = AIService(async_db_session, doc1)
    response = await service.process_query(text="نعم")
    assert response.success is True
    assert response.tool == "create_patient"


@pytest.mark.asyncio
async def test_authorized_doctor_can_confirm_visible_partial_name_and_blocks_hidden_partial_name(
    async_db_session, session_fixture
):
    """
    Confirming an action using a partial name ('Dynamic') for a canonically visible
    patient ('Dynamic Visibility Patient') must succeed via canonical search resolution,
    whereas confirming with a partial name for a hidden patient must be denied.
    """
    doc1 = session_fixture["doc1"]
    doc2 = session_fixture["doc2"]
    tenant_id = session_fixture["tenant1"].id

    # Hidden patient assigned to doc2
    hidden_patient = models.Patient(
        tenant_id=tenant_id,
        name="Ziad Hidden Patient",
        name_search_normalized=normalize_patient_name_for_search("Ziad Hidden Patient"),
        phone="01222222222",
        phone_search_hash=patient_phone_search_hash("01222222222"),
        age=45,
        assigned_doctor_id=doc2.id,
    )
    async_db_session.add(hidden_patient)
    await async_db_session.commit()

    # 1. Partial name 'Dynamic' for visible patient -> ALLOWED
    state_manager.update_session(
        tenant_id,
        doc1.id,
        {
            "active_patient_id": None,
            "active_patient_name": None,
            "pending_confirmation": {
                "tool": "create_appointment",
                "params": {
                    "patient_name": "Dynamic",
                    "date": "2026-04-20",
                    "time": "12:00",
                },
            },
        },
    )

    service = AIService(async_db_session, doc1)
    response = await service.process_query(text="نعم")
    assert response.success is True
    assert response.tool == "create_appointment"

    # 2. Partial name 'Ziad' for hidden patient -> DENIED
    state_manager.update_session(
        tenant_id,
        doc1.id,
        {
            "active_patient_id": None,
            "active_patient_name": None,
            "pending_confirmation": {
                "tool": "create_appointment",
                "params": {
                    "patient_name": "Ziad",
                    "date": "2026-04-20",
                    "time": "13:00",
                },
            },
        },
    )

    denied_response = await service.process_query(text="نعم")
    assert denied_response.success is False
    assert "صلاحية" in denied_response.message
