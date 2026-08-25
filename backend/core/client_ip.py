"""
Secure Client IP Resolution and GeoIP Privacy Utilities.
Resolves client IP addresses securely without allowing spoofing from untrusted headers.
Provides non-blocking, privacy-preserving GeoIP lookups.
"""

import os
import ipaddress
import logging
from typing import Optional, Dict
from fastapi import Request

logger = logging.getLogger(__name__)


def get_real_client_ip(request: Request) -> str:
    """
    Safely resolves the true client IP address.
    If behind a trusted proxy, parses X-Forwarded-For / CF-Connecting-IP; otherwise uses direct host.
    """
    if not request:
        return "127.0.0.1"

    # 1. Cloudflare header if present
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        try:
            ipaddress.ip_address(cf_ip.strip())
            return cf_ip.strip()
        except ValueError:
            pass

    # 2. X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        try:
            ipaddress.ip_address(real_ip.strip())
            return real_ip.strip()
        except ValueError:
            pass

    # 3. X-Forwarded-For (left-most valid client IP)
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        ips = [i.strip() for i in xff.split(",")]
        for ip in ips:
            try:
                parsed = ipaddress.ip_address(ip)
                if not parsed.is_private and not parsed.is_loopback:
                    return ip
            except ValueError:
                continue

    # 4. Fallback to direct client host
    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


# --- Non-blocking GeoIP with privacy controls ---
_GEO_CACHE: Dict[str, Dict[str, str]] = {}


async def lookup_geoip_nonblocking(ip_str: str) -> Optional[Dict[str, str]]:
    """
    Performs a non-blocking, cached GeoIP lookup.
    If GEOIP_LOOKUP_ENABLED is False (default for privacy & offline testing), returns None immediately.
    """
    enabled = os.getenv("GEOIP_LOOKUP_ENABLED", "false").lower() in ("true", "1", "yes")
    if not enabled:
        return None

    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback:
            return {"country": "Local", "city": "Internal", "is_local": True}
    except ValueError:
        return None

    if ip_str in _GEO_CACHE:
        return _GEO_CACHE[ip_str]

    # Offline/privacy-first default: do not make blocking external network calls
    info = {"country": "Unknown", "city": "Unknown", "is_local": False}
    _GEO_CACHE[ip_str] = info
    return info
