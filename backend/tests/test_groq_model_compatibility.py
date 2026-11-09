"""Groq developer-tier model compatibility, checked against docs on 2026-11-09.

Reference: https://console.groq.com/docs/deprecations and /docs/models.
Provider calls are the external boundary; no live key or clinical data is used.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from backend.ai.agent.core import AIAgent
from backend.ai.agent.router import SmartModelRouter
from backend.ai.analytics.service import AIAnalyticsService
from backend.services.ai_service import AIService
from backend.services.scribe_service import ScribeService


@pytest.fixture(autouse=True)
def isolate_provider_settings(monkeypatch):
    for key in ("GROQ_API_KEY", "GROQ_FAST_MODEL", "GROQ_COMPLEX_MODEL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")


@pytest.mark.parametrize("prompt,expected", [
    ("Hello", "openai/gpt-oss-20b"),
    ("حلل الطلب", "openai/gpt-oss-120b"),
])
def test_router_defaults_use_current_developer_tier_models(prompt, expected):
    assert SmartModelRouter.select_model(prompt) == expected


@pytest.mark.parametrize("setting,prompt,expected", [
    ("GROQ_FAST_MODEL", "Hello", "enterprise-fast"),
    ("GROQ_COMPLEX_MODEL", "حلل الطلب", "enterprise-complex"),
])
def test_router_honors_explicit_account_model_selection(monkeypatch, setting, prompt, expected):
    monkeypatch.setenv(setting, "  " + expected + "  ")
    assert SmartModelRouter.select_model(prompt) == expected


def test_agent_default_matches_current_fast_model():
    assert AIAgent().model == "openai/gpt-oss-20b"


@pytest.mark.asyncio
@pytest.mark.parametrize("override,expected", [
    (None, "openai/gpt-oss-20b"),
    ("enterprise-fast", "enterprise-fast"),
])
async def test_direct_analysis_uses_shared_fast_selection(monkeypatch, override, expected):
    if override:
        monkeypatch.setenv("GROQ_FAST_MODEL", override)
    db = Mock()
    db.commit = AsyncMock()
    service = AIService(db, SimpleNamespace(id=1, tenant_id=1, role="admin"))
    service._ensure_tenant_and_plan = AsyncMock()
    service._reserve_quota = AsyncMock(return_value=SimpleNamespace(
        reservation_id="synthetic-model-selection", status="RESERVED", is_replay=False,
    ))
    service._finalize_reservation = AsyncMock()
    provider = AsyncMock(return_value=SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content="Synthetic analysis")),
    ]))
    service.agent = SimpleNamespace(mock_mode=False, _call_llm_safe=provider)
    service.tenant = SimpleNamespace(id=1)
    monkeypatch.setattr("backend.services.ai_service.async_evaluate_commercial_ai_access", AsyncMock(return_value=None))

    response = await service.analyze_direct("Synthetic technical test; no clinical content")

    assert response.success
    assert provider.await_count == 1
    assert provider.call_args.args[0] == expected


@pytest.mark.parametrize("override,expected", [
    (None, "openai/gpt-oss-120b"),
    ("enterprise-complex", "enterprise-complex"),
])
def test_scribe_uses_shared_complex_selection(monkeypatch, override, expected):
    if override:
        monkeypatch.setenv("GROQ_COMPLEX_MODEL", override)
    service = ScribeService()
    provider = Mock(return_value=SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content='{"procedures": []}')),
    ]))
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=provider)))

    assert service.analyze_dictation("Synthetic technical test; no clinical content") == []
    assert provider.call_count == 1
    assert provider.call_args.kwargs["model"] == expected
    assert provider.call_args.kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
@pytest.mark.parametrize("recorded_cost,expected", [(0, 0.0003), (2.5, 2.5)])
async def test_model_change_preserves_existing_cost_estimate_and_recorded_cost(recorded_cost, expected):
    # Existing fallback: four requests, each estimated at 500 input + 500 output
    # tokens using legacy $0.05/$0.10 per million = 4 * 0.000075 = $0.0003.
    # An existing recorded sum of $2.50 must take precedence unchanged.
    results = [Mock(), Mock(), Mock(), Mock(), Mock(), Mock()]
    for item, value in zip(results[:3], [4, 4, recorded_cost]):
        item.scalar.return_value = value
    for item in results[3:]:
        item.all.return_value = []
    db = SimpleNamespace(execute=AsyncMock(side_effect=results))

    stats = await AIAnalyticsService.get_stats(db, tenant_id=1)

    assert stats["estimated_cost"] == expected
