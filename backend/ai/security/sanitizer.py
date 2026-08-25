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
        Mask credit card numbers, national IDs, and phone numbers that shouldn't be in output or sent unredacted.
        """
        if not text:
            return ""

        # Mask Egyptian National ID (14 digits starting with 2 or 3)
        text = re.sub(r"\b[23]\d{13}\b", "[REDACTED_NATIONAL_ID]", text)

        # Mask Egyptian Phone Numbers (local and international +20/0020 format)
        text = re.sub(r"(?:\+20|0020|0)?1[0125]\d{8}\b", "[REDACTED_PHONE]", text)

        # Mask Credit Cards (13-16 digits grouped or continuous)
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
