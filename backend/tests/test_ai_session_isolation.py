from types import SimpleNamespace

import pytest

from backend.services.ai_service import AIService


class FakeAgent:
    mock_mode = False

    def __init__(self):
        self.kwargs = None

    async def process(self, **kwargs):
        self.kwargs = kwargs
        return {"tool": "response", "message": "ok"}


class FakeDb:
    pass


@pytest.mark.asyncio
async def test_ai_agent_receives_authenticated_user_id(monkeypatch):
    user = SimpleNamespace(
        id=42,
        tenant_id=7,
        tenant=None,
        username="doctor42",
        role="doctor",
    )
    service = AIService(FakeDb(), user)
    agent = FakeAgent()
    service.agent = agent

    async def no_quota():
        return None

    async def no_confirmation(text, context):
        return None

    async def no_log(**kwargs):
        return None

    monkeypatch.setattr(service, "_check_subscription_quota", no_quota)
    monkeypatch.setattr(service, "_detect_confirmation", no_confirmation)
    monkeypatch.setattr(service, "_detect_intent", lambda text: None)
    monkeypatch.setattr(service, "_log_usage", no_log)

    result = await service.process_query("hello")

    assert result.success is True
    assert agent.kwargs["tenant_id"] == 7
    assert agent.kwargs["user_id"] == 42
