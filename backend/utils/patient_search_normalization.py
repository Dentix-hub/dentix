"""Patient search normalization for Arabic/MENA clinic workflows.

This module intentionally separates display data from searchable derivatives:
original patient names and encrypted phone values remain the source of truth.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import unicodedata
from typing import Literal, Optional

_ARABIC_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]"
)
_WHITESPACE_RE = re.compile(r"\s+")
_SEARCH_PUNCTUATION_RE = re.compile(r"[\u060C\u061B,;:/\\|_\-–—]+")

_DIGIT_TRANSLATION = str.maketrans(
    {
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    }
)

_ALEF_TRANSLATION = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
    }
)

SearchQueryType = Literal["empty", "file_number", "phone", "name"]


def normalize_digits(value: str | None) -> str:
    """Normalize Arabic-Indic and Persian digits to ASCII digits."""
    if value is None:
        return ""
    return str(value).translate(_DIGIT_TRANSLATION)


def normalize_patient_name_for_search(value: str | None) -> str:
    """Return a conservative Arabic-aware search representation.

    The stored/displayed name must never be replaced by this value.
    """
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = normalize_digits(normalized)
    normalized = normalized.replace("\u0640", "")
    normalized = _ARABIC_DIACRITICS_RE.sub("", normalized)
    normalized = normalized.translate(_ALEF_TRANSLATION)
    normalized = _SEARCH_PUNCTUATION_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized.casefold()


def normalize_egypt_phone(value: str | None) -> str:
    """Canonicalize common Egyptian phone formats without changing source data."""
    if value is None:
        return ""

    raw = normalize_digits(str(value)).strip()
    if not raw:
        return ""

    had_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""

    if digits.startswith("0020"):
        return "+20" + digits[4:]

    if raw.startswith("00") and len(digits) > 2:
        return "+" + digits[2:]

    if had_plus:
        return "+" + digits

    if digits.startswith("20") and len(digits) == 12:
        return "+" + digits

    if (
        len(digits) == 11
        and digits.startswith("01")
        and digits[2] in {"0", "1", "2", "5"}
    ):
        return "+20" + digits[1:]

    return digits


def _patient_search_hmac_key() -> bytes:
    """Derive a domain-separated key for blind patient-search indexes."""
    key_material = (
        os.getenv("PATIENT_SEARCH_HMAC_KEY")
        or os.getenv("ENCRYPTION_KEY")
        or os.getenv("SECRET_KEY")
    )
    if not key_material:
        raise RuntimeError(
            "Patient search key is not configured. Set PATIENT_SEARCH_HMAC_KEY "
            "or provide the existing ENCRYPTION_KEY/SECRET_KEY."
        )

    return hmac.new(
        key_material.encode("utf-8"),
        b"dentix:patient-search:v1",
        hashlib.sha256,
    ).digest()


def patient_phone_search_hash(value: str | None) -> Optional[str]:
    """Return a keyed deterministic blind index for exact phone lookup."""
    canonical_phone = normalize_egypt_phone(value)
    if not canonical_phone:
        return None

    return hmac.new(
        _patient_search_hmac_key(),
        canonical_phone.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def classify_patient_search_query(value: str | None) -> SearchQueryType:
    """Classify a patient-directory query for deterministic server search."""
    if not value or not str(value).strip():
        return "empty"

    normalized = normalize_digits(str(value)).strip()
    if normalized.startswith("#") and normalized[1:].strip().isdigit():
        return "file_number"

    digits = re.sub(r"\D", "", normalized)
    has_letters = any(ch.isalpha() for ch in normalized)

    if not has_letters and digits:
        if normalized.startswith(("+", "00", "01")) or 10 <= len(digits) <= 15:
            return "phone"
        if len(digits) <= 9:
            return "file_number"

    return "name"


def extract_file_number(value: str) -> Optional[int]:
    normalized = normalize_digits(value).strip()
    if normalized.startswith("#"):
        normalized = normalized[1:].strip()
    return int(normalized) if normalized.isdigit() else None


def escaped_like_pattern(normalized_query: str) -> str:
    """Build a token-friendly LIKE pattern and escape wildcard characters."""
    tokens = [token for token in normalized_query.split(" ") if token]
    escaped = []
    for token in tokens:
        token = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        escaped.append(token)
    return "%" + "%".join(escaped) + "%" if escaped else "%"
