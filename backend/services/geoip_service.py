import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class GeoIPService:
    @staticmethod
    def get_location(ip_address: str) -> Dict[str, Optional[str]]:
        """
        Get geographic location for an IP address.
        Uses ip-api.com (Free for non-commercial, no key required).
        """
        if not ip_address or ip_address in ["127.0.0.1", "::1", "localhost"]:
            return {"city": "Local", "country": "System", "country_code": "LOC", "isp": "Internal"}

        try:
            # Note: In a production environment, you should use a paid service or local MaxMind DB
            response = requests.get(f"http://ip-api.com/json/{ip_address}?fields=status,message,country,countryCode,city,isp", timeout=2)
            data = response.json()

            if data.get("status") == "success":
                return {
                    "city": data.get("city"),
                    "country": data.get("country"),
                    "country_code": data.get("countryCode"),
                    "isp": data.get("isp")
                }
        except Exception as e:
            logger.error(f"GeoIP Lookup Failed for {ip_address}: {e}")

        return {"city": "Unknown", "country": "Unknown", "country_code": "??", "isp": "Unknown"}
