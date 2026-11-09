"""Strict tool policy; NULL explicitly inherits the existing verified tool set."""

import json


def normalize_ai_tool_policy(raw: str | None) -> set[str] | None:
    if raw is None:
        return None
    value = json.loads(raw)
    if isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value):
        return set(value)
    if isinstance(value, dict) and all(
        isinstance(k, str) and k.strip() and type(v) is bool for k, v in value.items()
    ):
        return {key for key, allowed in value.items() if allowed}
    raise ValueError(
        "AI tools must be a JSON list or an object of boolean grants; NULL inherits"
    )
