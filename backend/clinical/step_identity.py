"""Bounded identities for free-form historical activities, separate from labels."""
import hashlib
import re
import unicodedata


def historical_step_identity(title: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", title).casefold().split())
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    # Retain the existing short ASCII identities for continuation compatibility.
    if normalized.isascii() and slug and len(slug) <= 64:
        return slug
    # Hash the complete Unicode label, so long common prefixes and non-Latin
    # activities cannot collapse to the same truncated/empty slug.
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{(slug or 'activity')[:47]}_{digest}"
