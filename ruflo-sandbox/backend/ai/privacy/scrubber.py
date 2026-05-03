"""
Privacy & PII Scrubbing Module
Sanitizes user input before sending to external LLM providers.
"""

import re
from typing import Tuple, Dict


class PIIScrubber:
    """
    Simple rule-based PII scrubber.
    In a real system, use NER models (Spacy/Presidio).
    """

    def __init__(self):
        # Temp store for mapping Alias -> Real Name
        self.mapping = {}  # In memory for single request scope (ideally passed around)

    @staticmethod
    def scrub(text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replaces sensitive patterns with aliases.
        Returns (scrubbed_text, alias_map).
        """
        aliases = {}
        scrubbed_text = text

        # 1. Phone Numbers (Egyptian 01xxxxxxxxx)
        # Replace with [PHONE-1], [PHONE-2]
        phone_matches = re.finditer(r"(01[0125][0-9]{8})", text)
        for i, match in enumerate(phone_matches):
            original = match.group(0)
            # Avoid re-scrubbing if already aliased (unlikely given regex)
            alias = f"[PHONE-{i + 1}]"
            aliases[alias] = original
            scrubbed_text = scrubbed_text.replace(original, alias, 1)

        # 2. National ID (Simplified 14 digits)
        nid_matches = re.finditer(r"\b\d{14}\b", text)
        for i, match in enumerate(nid_matches):
            original = match.group(0)
            alias = f"[NID-{i + 1}]"
            aliases[alias] = original
            scrubbed_text = scrubbed_text.replace(original, alias, 1)

        # Note: Names are hard without NLP. Reliability > Privacy here for strict medical context?
        # For now, we only scrub highly identifiable numbers.
        # Scrubbing names blindly might break "Search for Ahmed" -> "Search for [NAME-1]"
        # if the agent doesn't know [NAME-1] is Ahmed.

        return scrubbed_text, aliases

    @staticmethod
    def restore(text: str, aliases: Dict[str, str]) -> str:
        """Restores original PII from aliases."""
        if not aliases:
            return text

        restored_text = text
        for alias, original in aliases.items():
            restored_text = restored_text.replace(alias, original)
        return restored_text


# Singleton (stateless usage preferred)
scrubber = PIIScrubber()
