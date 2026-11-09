"""Static schema instructions must not look like an unredacted identity label.

Dynamic messages/context still pass through the complete existing egress guard.
"""
import pytest

from backend.ai.agent.prompt import build_system_prompt
from backend.services.ai_egress_policy import AIEgressDenied, prepare_ai_messages


@pytest.mark.parametrize("scribe_mode", [False, True])
def test_nonclinical_system_instructions_pass_deidentified_guard(monkeypatch, scribe_mode):
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    messages = [
        {"role": "system", "content": build_system_prompt(scribe_mode=scribe_mode)},
        {"role": "user", "content": "Synthetic technical verification, no actions."},
    ]

    prepared = prepare_ai_messages(messages)

    assert len(prepared) == 2
    assert '"patient_name"' in prepared[0]["content"]
    assert messages[1]["content"] == prepared[1]["content"]


@pytest.mark.parametrize("context", ["rag", "last_entity", "user"])
def test_dynamic_context_still_hits_confidence_gate(monkeypatch, context):
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    prompt = build_system_prompt(
        rag_context="MRN?" if context == "rag" else None,
        last_entity="MRN?" if context == "last_entity" else None,
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "MRN?" if context == "user" else "Synthetic check"},
    ]

    with pytest.raises(AIEgressDenied, match="confidence"):
        prepare_ai_messages(messages)


def test_actual_user_identifiers_are_still_redacted(monkeypatch):
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": "اسم المريض: أحمد اختبار، هاتف 01012345678"},
    ]

    prepared = prepare_ai_messages(messages)

    assert "أحمد" not in prepared[1]["content"]
    assert "01012345678" not in prepared[1]["content"]
    assert "[PERSON]" in prepared[1]["content"]


def test_default_deny_still_rejects_even_nonclinical_instructions(monkeypatch):
    monkeypatch.delenv("EXTERNAL_AI_PHI_MODE", raising=False)

    with pytest.raises(AIEgressDenied, match="disabled"):
        prepare_ai_messages([{"role": "system", "content": build_system_prompt()}])
