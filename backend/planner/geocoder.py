import time

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DeliveryPlannerDemo/1.0"

_last_request_time = 0.0


def _rate_limit():
    """Enforce 1 request per second for Nominatim."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_request_time = time.monotonic()


def geocode_address(address: str) -> tuple[float, float] | None:
    """
    Geocode a single address via Nominatim.
    Returns (lat, lng) or None if not found.
    """
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
            return None

        return float(results[0]["lat"]), float(results[0]["lon"])

    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None
