"""Single fail-closed policy boundary for every external AI provider call."""

from __future__ import annotations

import logging
import os
import re
from copy import deepcopy
from typing import Any

from backend.core.config import get_external_ai_phi_mode

logger = logging.getLogger(__name__)


class AIEgressDenied(RuntimeError):
    """Raised before a provider call when privacy policy denies the egress."""


_TRUE = {"1", "true", "yes"}
_REDACTIONS = (
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+?20)?01[0125]\d{8}(?!\d)"), "[PHONE]"),
    (re.compile(r"(?<!\d)\d{14}(?!\d)"), "[NATIONAL_ID]"),
    (re.compile(r"\b(?:MRN|record|file|patient)[\s:#-]*(?:no\.?\s*)?[A-Z0-9-]{3,}\b", re.I), "[RECORD_ID]"),
    (re.compile(r"\b(?:19|20)\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])\b"), "[DATE]"),
    (re.compile(r"\b(?:name|patient name)\s*[:=-]\s*[\w\u0600-\u06ff]+(?:\s+[\w\u0600-\u06ff]+){0,3}", re.I), "name: [PERSON]"),
    (re.compile(r"(?:اسم\s+المريض|المريض)\s*[:=-]?\s*[\u0600-\u06ff]+(?:\s+[\u0600-\u06ff]+){0,3}"), "اسم المريض: [PERSON]"),
    (re.compile(r"\b(?:address|lives? at)\s*[:=-]\s*[^\n,;]{3,80}", re.I), "address: [ADDRESS]"),
    (re.compile(r"(?:العنوان|يسكن في)\s*[:=-]?\s*[^\n،;]{3,80}"), "العنوان: [ADDRESS]"),
)
_RESIDUAL_HIGH_RISK = (
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)(?:\+?20)?01[0125]\d{8}(?!\d)"),
    re.compile(r"(?<!\d)\d{10,14}(?!\d)"),
    re.compile(r"\b(?:MRN|national id|الرقم القومي)\b", re.I),
    re.compile(r"(?:patient name|اسم المريض)(?!\s*:\s*\[PERSON\])", re.I),
)


def _deidentify(text: str) -> str:
    sanitized = text
    for pattern, replacement in _REDACTIONS:
        sanitized = pattern.sub(replacement, sanitized)
    if any(pattern.search(sanitized) for pattern in _RESIDUAL_HIGH_RISK):
        raise AIEgressDenied("AI de-identification confidence gate rejected the payload")
    return sanitized


def prepare_ai_messages(
    messages: list[dict[str, Any]], *, tenant_id: int | None = None
) -> list[dict[str, Any]]:
    """Authorize and transform provider messages without logging their content."""
    mode = get_external_ai_phi_mode()
    if mode == "deny":
        logger.warning("External AI egress denied by policy", extra={"tenant_id": tenant_id})
        raise AIEgressDenied("External AI processing is disabled by privacy policy")

    if mode == "contracted":
        approved = os.getenv("EXTERNAL_AI_CONTRACT_APPROVED", "false").strip().lower()
        if approved not in _TRUE:
            logger.error(
                "External AI contracted mode lacks approval marker",
                extra={"tenant_id": tenant_id},
            )
            raise AIEgressDenied("External AI contractual approval is not configured")
        return deepcopy(messages)

    prepared = deepcopy(messages)
    for message in prepared:
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = _deidentify(content)
        elif content is not None:
            raise AIEgressDenied("Unsupported AI message content cannot be de-identified")
    logger.info("External AI payload de-identified", extra={"tenant_id": tenant_id})
    return prepared
