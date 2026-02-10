"""
AI Output Sanitizer.
Ensures AI responses are safe for frontend rendering and do not leak sensitive info.
"""

import re
from typing import Dict, Any


class AISanitizer:
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Strip potentially dangerous HTML tags.
        Allows basic formatting (b, i, u, br, p, ul, li).
        """
        if not text:
            return ""

        # Remove script and style tags completely content and all
        text = re.sub(
            r"<(script|style|iframe|object|embed)[^>]*>.*?</\1>",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove on* events
        text = re.sub(r' on\w+="[^"]*"', "", text, flags=re.IGNORECASE)

        # For now, we rely on React to escape HTML by default unless dangerouslySetInnerHTML is used.
        # But if the AI outputs Markdown that gets converted to HTML, we want to be sure.
        # Simple policy: Escape < and > unless explicitly needed?
        # Better: Just ensure no script tags exist.

        return text

    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        """
        Mask credit card numbers or other sensitive patterns that shouldn't be in output.
        (Note: PII restoring happens separatly, this is for accidental leaks)
        """
        # Mask Credit Cards (Social Engineering protection)
        # Matches 13-19 digits, possibly separated by spaces or dashes
        # Strict enough to avoid masking everything
        text = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[HIDDEN_CARD]", text)

        return text

    @staticmethod
    def sanitize_response_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize data dictionary.
        """
        clean_data = {}
        for k, v in data.items():
            if isinstance(v, str):
                clean_data[k] = AISanitizer.sanitize_html(v)
            elif isinstance(v, dict):
                clean_data[k] = AISanitizer.sanitize_response_data(v)
            elif isinstance(v, list):
                clean_data[k] = [
                    AISanitizer.sanitize_response_data(i)
                    if isinstance(i, dict)
                    else (AISanitizer.sanitize_html(i) if isinstance(i, str) else i)
                    for i in v
                ]
            else:
                clean_data[k] = v
        return clean_data
