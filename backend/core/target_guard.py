"""
DENTIX Target Guard
Guards local database and HTTP test operations from accidentally targeting live/hosted environments.
"""

import os
import re
from urllib.parse import urlparse


class UnsafeTargetError(ValueError):
    """Raised when a target host or database is determined to be non-local or unsafe."""
    pass


FORBIDDEN_HOST_PATTERNS = [
    r"dentixs\.app",
    r"supabase\.co",
    r"vercel\.app",
    r"hf\.space",
    r"huggingface\.co",
    r"digitalocean\.com",
    r"aws\.amazon\.com",
    r"render\.com",
    r"railway\.app",
]

ALLOWED_LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "host.docker.internal",
    "postgres",
    "db",
}

ALLOWED_DB_NAME_PATTERNS = [
    r"test",
    r"ci",
    r"ephemeral",
    r"dentix_local",
    r"dentix_dev",
    r"dentix_test",
]


def sanitize_target_url(url_str: str) -> str:
    """Strip password/credentials from a URL or connection string for safe logging."""
    if not url_str:
        return ""
    try:
        parsed = urlparse(url_str)
        if parsed.password:
            sanitized_netloc = parsed.netloc.replace(f":{parsed.password}", ":***")
            return parsed._replace(netloc=sanitized_netloc).geturl()
        return url_str
    except Exception:
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url_str)


def validate_database_target(db_url: str, is_destructive: bool = False) -> str:
    """
    Validate that a database URL points strictly to a local, ephemeral, or test database.
    Returns the sanitized database target string.
    Raises UnsafeTargetError if target is prohibited.
    """
    if not db_url:
        raise UnsafeTargetError("Database target URL cannot be empty.")

    # Normalize url scheme if asyncpg
    norm_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        parsed = urlparse(norm_url)
    except Exception as e:
        raise UnsafeTargetError(f"Malformed database URL: {e}")

    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lstrip("/").lower()

    # Check forbidden host substrings
    for pattern in FORBIDDEN_HOST_PATTERNS:
        if re.search(pattern, host):
            raise UnsafeTargetError(f"Database host '{host}' matches forbidden pattern '{pattern}'.")

    # Ensure host is an allowed local/container host
    if host not in ALLOWED_LOCAL_HOSTS and not host.endswith(".local"):
        raise UnsafeTargetError(f"Database host '{host}' is not an authorized local or container host.")

    # Validate database name contains allowed test/local pattern
    db_name_allowed = any(re.search(p, path) for p in ALLOWED_DB_NAME_PATTERNS)
    if not db_name_allowed:
        raise UnsafeTargetError(
            f"Database name '{path}' must contain one of: test, ci, ephemeral, dentix_local, dentix_dev."
        )

    if is_destructive:
        if os.getenv("LOCAL_DESTRUCTIVE_TESTS") != "1":
            raise UnsafeTargetError(
                "Destructive operations require LOCAL_DESTRUCTIVE_TESTS=1 environment variable."
            )

    return sanitize_target_url(db_url)


def validate_http_target(url_str: str) -> str:
    """
    Validate that an HTTP target for tests/load tests is strictly loopback/localhost.
    Returns the sanitized target URL.
    Raises UnsafeTargetError if target is prohibited.
    """
    if not url_str:
        raise UnsafeTargetError("HTTP target URL cannot be empty.")

    try:
        parsed = urlparse(url_str)
    except Exception as e:
        raise UnsafeTargetError(f"Malformed HTTP URL: {e}")

    host = (parsed.hostname or "").lower()
    for pattern in FORBIDDEN_HOST_PATTERNS:
        if re.search(pattern, host):
            raise UnsafeTargetError(f"HTTP host '{host}' matches forbidden pattern '{pattern}'.")

    if host not in ALLOWED_LOCAL_HOSTS:
        raise UnsafeTargetError(f"HTTP host '{host}' is not an allowed local target.")

    return sanitize_target_url(url_str)
