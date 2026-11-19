import hashlib
import logging
import time

import requests
from django.conf import settings

from .budapest import BBOX, ZIP_CENTROIDS, in_budapest
from .districts import extract_postal_code

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DeliveryPlannerDemo/1.0 (lastmile-c07a.onrender.com)"

CITY_CENTRE = (47.4979, 19.0402)
MOCK_JITTER_DEG = 0.004  # ~400 m

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
    """Offline stand-in for Nominatim: the address lands in its own postal code's area.

    Deterministic. The postal code picks the centroid (so addresses of one zip cluster together, like
    real ones); the street/number hash only spreads them ~400 m around it. Without a known postal code
    the point falls near the Budapest centre, never at a random place on the map.
    """
    h = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
    lat0, lng0 = ZIP_CENTROIDS.get(extract_postal_code(address) or "", CITY_CENTRE)
    lat = lat0 + ((h % 2000) / 2000 - 0.5) * 2 * MOCK_JITTER_DEG
    lng = lng0 + (((h >> 16) % 2000) / 2000 - 0.5) * 2 * MOCK_JITTER_DEG
    return (lat, lng)


def geocode_address(address: str) -> tuple[float, float] | None:
    """
    Geocode a single address via Nominatim.
    Returns (lat, lng) or None if not found.
    In E2E mock mode, returns deterministic fake coordinates.
    """
    if settings.E2E_MOCK:
        # Deterministic miss for e2e: a city-less address marked 'nocity' is not found,
        # exactly like a real recipient forgetting the city. Appending the city fixes it.
        lowered = address.lower()
        if "nocity" in lowered and "budapest" not in lowered:
            return None
        return _mock_geocode(address)

    _rate_limit()

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": address,
                "format": "jsonv2",
                "limit": 1,
                # Budapest only: an address must never resolve to a same-named street elsewhere.
                "countrycodes": "hu",
                "viewbox": f"{BBOX[1]},{BBOX[2]},{BBOX[3]},{BBOX[0]}",
                "bounded": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()

        if not results:
            logger.warning("Nominatim returned no results for: %s", address)
            return None

        lat, lng = float(results[0]["lat"]), float(results[0]["lon"])
        if not in_budapest(lat, lng):
            logger.warning("Nominatim hit outside Budapest for '%s': %s,%s", address, lat, lng)
            return None
        return lat, lng

    except requests.RequestException as e:
        logger.error("Nominatim request failed for '%s': %s", address, e)
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error("Nominatim response parse error for '%s': %s", address, e)
        return None
