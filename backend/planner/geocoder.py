import hashlib
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DeliveryPlannerDemo/1.0 (lastmile-c07a.onrender.com)"

_last_request_time = 0.0


def _rate_limit():
    """Enforce 1 request per second for Nominatim."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_request_time = time.monotonic()


def _mock_geocode(address: str) -> tuple[float, float]:
    """Return deterministic fake coordinates in Budapest area based on address hash."""
    h = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
    lat = 47.4 + (h % 2000) / 10000  # 47.40 - 47.60
    lng = 19.0 + ((h >> 16) % 2000) / 10000  # 19.00 - 19.20
    return (lat, lng)


def geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode a single address via Nominatim, returning (lat, lng) or None.

    Honors the 1 req/sec Nominatim rate limit via `_rate_limit()`. In
    E2E mock mode (`settings.E2E_MOCK`), returns deterministic
    Budapest-area coordinates without contacting the network so tests
    stay hermetic.
    """
    if settings.E2E_MOCK:
        return _mock_geocode(address)

    _rate_limit()

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": address,
                "format": "jsonv2",
                "limit": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()

        if not results:
            logger.warning("Nominatim returned no results for: %s", address)
            return None

        return float(results[0]["lat"]), float(results[0]["lon"])

    except requests.RequestException as e:
        logger.error("Nominatim request failed for '%s': %s", address, e)
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error("Nominatim response parse error for '%s': %s", address, e)
        return None
