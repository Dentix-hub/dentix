"""
DENTIX Bounded Logging and Error Sanitizer.
Scrubs passwords, tokens, API keys, database credentials, National IDs, and Egyptian mobile phone numbers
from log records, exception traces, and persisted SystemError rows. Enforces strict length bounds.
"""

import logging
import re
from typing import Any, Dict, Optional

# Regular expressions for sensitive patterns
PATTERNS = [
    # 1. Bearer / JWT Tokens
    (re.compile(r"Bearer\s+([A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+)", re.IGNORECASE), "Bearer [REDACTED_JWT]"),
    (re.compile(r"\beyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+\b"), "[REDACTED_JWT]"),

    # 2. Passwords / Secrets in URLs
    (re.compile(r"(://[^:\s@]+):([^@\s/]+)@"), r"\1:[REDACTED_SECRET]@"),

    # 3. Password / Secret / Token JSON or query parameters
    (re.compile(r'(["\']?(?:password|passwd|new_password|old_password|otp_secret|secret|access_token|refresh_token|token|api_key|master_code)["\']?\s*[:=]\s*["\'])([^"\'\s&,]+)(["\']?)', re.IGNORECASE), r'\1[REDACTED]\3'),

    # 4. Egyptian National ID (14 digits starting with 2 or 3)
    (re.compile(r"\b([23]\d{2})(\d{8})(\d{3})\b"), r"\1********\3"),

    # 5. Egyptian Mobile Phone (11 digits starting with 010, 011, 012, 015)
    (re.compile(r"\b(01[0125])\d{4}(\d{4})\b"), r"\1****\2"),

    # 6. Private Keys
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
]

DEFAULT_MAX_TEXT_LENGTH = 4000
DEFAULT_MAX_TRACE_LENGTH = 12000


def sanitize_text(text: Optional[str], max_length: int = DEFAULT_MAX_TEXT_LENGTH) -> Optional[str]:
    """Sanitizes text by removing secrets, credentials, and PHI, and capping length."""
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)

    sanitized = text
    for pattern, replacement in PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + " ... [TRUNCATED]"

    return sanitized


def sanitize_stack_trace(stack_trace: Optional[str], max_length: int = DEFAULT_MAX_TRACE_LENGTH) -> Optional[str]:
    """Sanitizes an exception stack trace, ensuring sensitive query parameters or secrets are scrubbed."""
    return sanitize_text(stack_trace, max_length=max_length)


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize dictionary values for safe logging/serialization."""
    sanitized = {}
    for k, v in data.items():
        key_lower = str(k).lower()
        if any(secret_term in key_lower for secret_term in ["password", "passwd", "secret", "token", "key", "otp"]):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, str):
            sanitized[k] = sanitize_text(v)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [sanitize_text(item) if isinstance(item, str) else item for item in v]
        else:
            sanitized[k] = v
    return sanitized


class BoundedSanitizingFilter(logging.Filter):
    """Logging filter that scrubs sensitive information from LogRecord messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = sanitize_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_text(a) if isinstance(a, str) else a for a in record.args
                )
        return True
