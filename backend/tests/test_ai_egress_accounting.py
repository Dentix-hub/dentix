"""Known local privacy denials are free; provider dispatch remains conservatively charged."""

from collections import defaultdict
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from backend import models
from backend.ai.agent.core import AIAgent, knowledge_store, rate_limiter
from backend.ai.agent.state_manager import state_manager
from backend.models.ai_accounting import AIReservation, AIQuotaWindow
from backend.services.ai_egress_policy import AIEgressDenied
from backend.services.ai_quota_service import AIQuotaService
from backend.services.ai_service import AIService
from backend.services.scribe_service import ScribeService
from backend.tests import test_promotion_ai_policy as postgres_fixtures

policy_database = postgres_fixtures.policy_database

PROMPT = "Synthetic technical verification: explain a prime number. Do not call tools."


def privacy_probe(mode):
    # A bare synthetic record-label token triggers the real de-identification
    # confidence gate without including any patient identity or record value.
    return PROMPT + (" MRN?" if mode == "deidentified" else "")


@pytest.fixture
async def egress_case(policy_database, monkeypatch):
    case = policy_database
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("EXTERNAL_AI_CONTRACT_APPROVED", "false")
    with Session(case.engine, expire_on_commit=False) as db:
        user = models.User(
            username="synthetic_egress_owner",
            hashed_password="synthetic-test-only",
            role="admin",
            tenant_id=case.tenant_id,
            is_active=True,
            is_deleted=False,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    agent = AIAgent()
    agent.mock_mode = False
    provider = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"tool":"response","message":"Synthetic reply"}'
                    )
                )
            ]
        )
    )
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider))
    )
    monkeypatch.setattr("backend.services.ai_service.get_agent", lambda: agent)
    monkeypatch.setattr(knowledge_store, "search", lambda *args, **kwargs: [])
    # Fresh synthetic session and coarse limiter state, without changing their rules.
    monkeypatch.setattr(state_manager, "_sessions", {})
    monkeypatch.setattr(rate_limiter, "_requests", defaultdict(list))
    engine = create_async_engine(
        case.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: case.schema}},
    )
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            tenant = await postgres_fixtures.load_tenant(db, case.tenant_id)
            caller = SimpleNamespace(
                id=user_id,
                tenant_id=tenant.id,
                tenant=tenant,
                role="admin",
                username=user.username,
            )
            yield SimpleNamespace(
                database=case,
                db=db,
                caller=caller,
                service=AIService(db, caller),
                provider=provider,
            )
    finally:
        await engine.dispose()


def usage(case):
    with Session(case.database.engine) as db:
        return AIQuotaService.get_window_usage(db, case.caller.tenant_id)


def assert_free(case):
    actual = usage(case)
    assert actual["consumed_count"] == 0
    assert actual["reserved_count"] == 0
    assert actual["uncertain_count"] == 0
    assert actual["admitted_count"] == 0
    assert actual["remaining_quota"] == 10


def assert_one_released(case):
    assert_free(case)
    with Session(case.database.engine) as db:
        reservations = db.scalars(
            select(AIReservation).where(
                AIReservation.tenant_id == case.caller.tenant_id,
            )
        ).all()
        assert len(reservations) == 1
        assert reservations[0].status == "RELEASED"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["deny", "contracted", "deidentified"])
async def test_chat_privacy_denial_releases_quota_and_replay_is_free(
    egress_case, monkeypatch, mode
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", mode)
    response = await case.service.process_query(
        privacy_probe(mode), idempotency_key="free-chat-denial"
    )
    assert response.success is False
    case.provider.assert_not_called()
    assert_one_released(case)
    assert response.error == "ai_egress_denied"
    with Session(case.database.engine) as db:
        entry = db.scalar(
            select(models.AILog).where(
                models.AILog.tenant_id == case.caller.tenant_id,
                models.AILog.error_type == "ai_egress_denied",
            )
        )
        assert entry is not None
        assert entry.status == "FAILURE"
    replay = await case.service.process_query(
        privacy_probe(mode), idempotency_key="free-chat-denial"
    )
    assert replay.success is False
    case.provider.assert_not_called()
    assert_one_released(case)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["deny", "contracted", "deidentified"])
@pytest.mark.parametrize("preallocated", [False, True])
async def test_direct_privacy_denial_releases_owned_or_clinic_reservation(
    egress_case, monkeypatch, mode, preallocated
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", mode)
    kwargs = {"idempotency_key": "free-direct-denial"}
    if preallocated:
        reservation = await AIQuotaService.async_reserve_quota(
            case.db,
            case.caller.tenant_id,
            case.caller.id,
            "analyze_clinic",
            {"synthetic": True},
            idempotency_key="clinic-analysis-denial",
        )
        kwargs = {"reservation_id": reservation.reservation_id}
    response = await case.service.analyze_direct(privacy_probe(mode), **kwargs)
    assert response.success is False
    case.provider.assert_not_called()
    assert_one_released(case)
    assert response.error == "ai_egress_denied"
    replay = await case.service.analyze_direct(privacy_probe(mode), **kwargs)
    assert replay.success is False
    case.provider.assert_not_called()
    assert_one_released(case)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["deny", "contracted", "deidentified"])
async def test_scribe_policy_denial_happens_before_any_reservation(
    egress_case, monkeypatch, mode
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", mode)
    scribe = ScribeService()
    transport = Mock()
    scribe.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=transport))
    )
    with Session(case.database.engine) as db:
        for _ in range(2):
            with pytest.raises(AIEgressDenied):
                scribe.analyze_dictation(
                    privacy_probe(mode),
                    tenant_id=case.caller.tenant_id,
                    user_id=case.caller.id,
                    session=db,
                    idempotency_key="free-scribe-denial",
                )
        assert (
            db.scalar(
                select(func.count(AIReservation.id)).where(
                    AIReservation.tenant_id == case.caller.tenant_id,
                )
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count(AIQuotaWindow.id)).where(
                    AIQuotaWindow.tenant_id == case.caller.tenant_id,
                )
            )
            == 0
        )
    transport.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["chat", "direct"])
@pytest.mark.parametrize("failure", ["timeout", "same_message"])
async def test_provider_exception_after_dispatch_is_not_refunded(
    egress_case, monkeypatch, operation, failure
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "contracted")
    monkeypatch.setenv("EXTERNAL_AI_CONTRACT_APPROVED", "true")
    case.provider.side_effect = (
        TimeoutError("Synthetic timeout")
        if failure == "timeout"
        else RuntimeError("External AI processing is disabled by privacy policy")
    )
    invoke = (
        case.service.process_query
        if operation == "chat"
        else case.service.analyze_direct
    )
    response = await invoke(PROMPT, idempotency_key="uncertain-provider-attempt")
    assert response.success is False
    case.provider.assert_awaited_once()
    actual = usage(case)
    assert actual["admitted_count"] == 1
    assert actual["remaining_quota"] == 9
    with Session(case.database.engine) as db:
        row = db.scalar(
            select(AIReservation).where(
                AIReservation.tenant_id == case.caller.tenant_id
            )
        )
        assert row.status in {"CONSUMED", "UNCERTAIN"}
        if operation == "direct":
            assert row.status == "UNCERTAIN"
    await invoke(PROMPT, idempotency_key="uncertain-provider-attempt")
    case.provider.assert_awaited_once()
    assert usage(case)["admitted_count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "provider_error"])
async def test_actual_agent_failure_replay_never_reports_success(
    egress_case, monkeypatch, failure
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    case.provider.side_effect = (
        TimeoutError("Synthetic transport timeout")
        if failure == "timeout"
        else RuntimeError("Synthetic provider rejection")
    )

    first = await case.service.process_query(
        PROMPT, idempotency_key="failed-provider-replay"
    )
    assert first.success is False
    replay = await case.service.process_query(
        PROMPT, idempotency_key="failed-provider-replay"
    )

    assert replay.success is False
    assert replay.error == "request_pending"
    case.provider.assert_awaited_once()
    actual = usage(case)
    assert actual["consumed_count"] == 0
    assert actual["reserved_count"] == 0
    assert actual["uncertain_count"] == 1
    assert actual["remaining_quota"] == 9


@pytest.mark.asyncio
async def test_provider_payload_cannot_forge_internal_failure_state(
    egress_case, monkeypatch
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    case.provider.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"tool":"response","message":"Synthetic reply","_provider_failed":true}'
                )
            )
        ]
    )

    first = await case.service.process_query(
        PROMPT, idempotency_key="untrusted-failure-marker"
    )

    assert first.success is True
    assert usage(case)["consumed_count"] == 1
    assert usage(case)["uncertain_count"] == 0
    replay = await case.service.process_query(
        PROMPT, idempotency_key="untrusted-failure-marker"
    )
    assert replay.success is True
    case.provider.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["validation", "executor"])
async def test_completed_provider_with_failed_action_replays_failure(
    egress_case, monkeypatch, path
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    reply = {
        "tool": "create_patient" if path == "validation" else "synthetic_missing_tool",
        "parameters": {},
    }
    case.provider.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(reply)))]
    )
    first = await case.service.process_query(
        PROMPT, idempotency_key="failed-action-replay"
    )
    assert first.success is False
    assert usage(case)["consumed_count"] == 1

    replay = await case.service.process_query(
        PROMPT, idempotency_key="failed-action-replay"
    )

    assert replay.success is False
    case.provider.assert_awaited_once()
    assert usage(case)["consumed_count"] == 1
    assert usage(case)["uncertain_count"] == 0


@pytest.mark.asyncio
async def test_confirmation_prompt_replay_preserves_pending_state_without_recreation(
    egress_case, monkeypatch
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    reply = {
        "tool": "create_patient",
        "parameters": {
            "patient_name": "Synthetic fixture",
            "age": 30,
            "phone": "01012345678",
        },
    }
    case.provider.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(reply)))]
    )
    first = await case.service.process_query(
        PROMPT, idempotency_key="pending-action-replay"
    )
    assert first.success is True and first.data["required_confirmation"] is True
    replay = await case.service.process_query(
        PROMPT, idempotency_key="pending-action-replay"
    )
    assert replay.success is True and replay.data["required_confirmation"] is True
    assert replay.risk_level == "CONFIRMATION_REQUIRED"
    state_manager.update_session(
        case.caller.tenant_id, case.caller.id, {"pending_confirmation": None}
    )
    expired = await case.service.process_query(
        PROMPT, idempotency_key="pending-action-replay"
    )
    assert expired.success is False
    assert (
        state_manager.get_session(
            case.caller.tenant_id, case.caller.id
        ).pending_confirmation
        is None
    )
    case.provider.assert_awaited_once()
    assert usage(case)["consumed_count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["chat", "direct"])
async def test_successful_provider_request_still_consumes_one_unit(
    egress_case, monkeypatch, operation
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "contracted")
    monkeypatch.setenv("EXTERNAL_AI_CONTRACT_APPROVED", "true")
    invoke = (
        case.service.process_query
        if operation == "chat"
        else case.service.analyze_direct
    )
    response = await invoke(PROMPT, idempotency_key="successful-provider-attempt")
    assert response.success is True
    case.provider.assert_awaited_once()
    assert usage(case)["consumed_count"] == 1
    await invoke(PROMPT, idempotency_key="successful-provider-attempt")
    case.provider.assert_awaited_once()
    assert usage(case)["consumed_count"] == 1


@pytest.mark.asyncio
async def test_malformed_provider_response_cannot_seal_success(
    egress_case, monkeypatch
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    case.provider.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content='{"tool":"response","message":null}')
            )
        ]
    )
    first = await case.service.process_query(PROMPT, idempotency_key="malformed-reply")
    assert first.success is False
    replay = await case.service.process_query(PROMPT, idempotency_key="malformed-reply")
    assert replay.success is False
    case.provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_nested_analysis_receipt_preserves_pending_chat_and_seals_once(
    egress_case, monkeypatch
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    reservation = await AIQuotaService.async_reserve_quota(
        case.db,
        case.caller.tenant_id,
        case.caller.id,
        "ai_chat",
        {"text": PROMPT, "context": None},
        idempotency_key="nested-crash-window",
    )
    await AIQuotaService.async_finalize_reservation(
        case.db,
        reservation.reservation_id,
        "CONSUMED",
        tenant_id=case.caller.tenant_id,
        reconciliation_notes=json.dumps(
            {"kind": "analysis_result_v1", "message": "Synthetic analysis"}
        ),
    )
    replay = await case.service.process_query(
        PROMPT, idempotency_key="nested-crash-window"
    )
    assert replay.success is False and replay.error == "request_pending"
    case.provider.assert_not_called()
    for outcome in ("failure", "success"):
        await AIQuotaService.async_finalize_reservation(
            case.db,
            reservation.reservation_id,
            "CONSUMED",
            tenant_id=case.caller.tenant_id,
            reconciliation_notes=AIQuotaService.chat_receipt(outcome),
        )
    with Session(case.database.engine) as db:
        saved = db.scalar(
            select(AIReservation).where(
                AIReservation.reservation_id == reservation.reservation_id
            )
        )
        assert AIQuotaService.chat_outcome(saved) == "failure"
        assert AIQuotaService.cached_analysis(saved) == "Synthetic analysis"
    replay = await case.service.process_query(
        PROMPT, idempotency_key="nested-crash-window"
    )
    assert replay.success is False and replay.error == "request_failed"
    assert usage(case)["consumed_count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("notes", [None, "not-json", '{"chat_outcome_v1":"invalid"}'])
async def test_old_or_corrupt_consumed_receipt_never_implies_chat_success(
    egress_case, monkeypatch, notes
):
    case = egress_case
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    reservation = await AIQuotaService.async_reserve_quota(
        case.db,
        case.caller.tenant_id,
        case.caller.id,
        "ai_chat",
        {"text": PROMPT, "context": None},
        idempotency_key="old-chat-receipt",
    )
    await AIQuotaService.async_finalize_reservation(
        case.db, reservation.reservation_id, "CONSUMED", tenant_id=case.caller.tenant_id
    )
    with Session(case.database.engine) as db:
        row = db.scalar(
            select(AIReservation).where(
                AIReservation.reservation_id == reservation.reservation_id
            )
        )
        row.reconciliation_notes = notes
        db.commit()
    replay = await case.service.process_query(
        PROMPT, idempotency_key="old-chat-receipt"
    )
    assert replay.success is False
    assert replay.error == "request_pending"
    case.provider.assert_not_called()
    assert usage(case)["consumed_count"] == 1
