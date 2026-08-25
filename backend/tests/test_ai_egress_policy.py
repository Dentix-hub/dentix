from unittest.mock import Mock

import pytest

from backend.services.ai_egress_policy import AIEgressDenied, prepare_ai_messages
from backend.services.scribe_service import ScribeService


def test_default_deny_stops_provider_before_call(monkeypatch):
    monkeypatch.delenv("EXTERNAL_AI_PHI_MODE", raising=False)
    service = ScribeService()
    service.client = Mock()

    with pytest.raises(AIEgressDenied, match="disabled"):
        service.analyze_dictation("اسم المريض أحمد لديه تسوس", tenant_id=7)

    service.client.chat.completions.create.assert_not_called()


def test_deidentified_mode_removes_named_clinical_identifiers(monkeypatch):
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    prepared = prepare_ai_messages(
        [{"role": "user", "content": "اسم المريض: أحمد علي، هاتف 01012345678، تاريخ 2026-08-25"}],
        tenant_id=7,
    )

    content = prepared[0]["content"]
    assert "أحمد" not in content
    assert "01012345678" not in content
    assert "2026-08-25" not in content
    assert "[PERSON]" in content


def test_contracted_mode_requires_explicit_approval(monkeypatch):
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "contracted")
    monkeypatch.delenv("EXTERNAL_AI_CONTRACT_APPROVED", raising=False)

    with pytest.raises(AIEgressDenied, match="approval"):
        prepare_ai_messages([{"role": "user", "content": "clinical text"}])


def test_contracted_mode_preserves_payload_only_after_approval(monkeypatch):
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "contracted")
    monkeypatch.setenv("EXTERNAL_AI_CONTRACT_APPROVED", "true")
    payload = [{"role": "user", "content": "clinical text"}]

    assert prepare_ai_messages(payload) == payload
