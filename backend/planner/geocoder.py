import hashlib
import logging
import re
import threading
import time

import requests
from django.conf import settings

from .budapest import BBOX, ZIP_CENTROIDS, haversine_km, in_budapest
from .districts import extract_postal_code
from .timing import DEPOT

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


_HOUSE_NO_RE = re.compile(r"(\d+[a-zA-Z]?(?:\s*[-/]\s*(?:\d+[a-zA-Z]?|[a-zA-Z]))?)\s*\.?$")


def requested_house_number(address: str) -> str | None:
    """The house number a planner typed: the last number group once postal code and city are removed."""
    cleaned = re.sub(r"\b1\d{3}\b", " ", address)  # postal code
    cleaned = re.sub(r"(?i)\bbudapest\b|\bh-", " ", cleaned).strip(" ,;.")
    m = _HOUSE_NO_RE.search(cleaned)
    return re.sub(r"\s+", "", m.group(1)).lower() if m else None


def _number_parts(value: str) -> tuple[int, int] | None:
    nums = [int(n) for n in re.findall(r"\d+", value)]
    return (nums[0], nums[-1]) if nums else None


def _house_matches(requested: str, found: str | None) -> bool:
    """Exact house number, or the requested number lies inside the found range ('1' in '1-3')."""
    if not found:
        return False
    found = re.sub(r"\s+", "", found).lower().rstrip(".")
    if requested == found:
        return True
    req, fnd = _number_parts(requested), _number_parts(found)
    if not req or not fnd or "/" in requested or req[0] != req[1]:
        return False
    return fnd[0] <= req[0] <= fnd[1] and not requested[-1].isalpha()


def _is_address_point(r: dict) -> bool:
    return (r.get("category"), r.get("type")) == ("place", "house")


POINT_EXTENT_M = 8.0  # Nominatim pads a point's bounding box to ~7 m; buildings/areas are far larger


def _extent_m(r: dict) -> float | None:
    """Half-diagonal (m) of the result's bounding box: ~7 for a map point, 28-220 for a building or area."""
    try:
        south, north, west, east = (float(v) for v in r["boundingbox"])
    except (KeyError, ValueError, TypeError):
        return None
    return haversine_km((south, west), (north, east)) * 500


def _median(values):
    values = sorted(values)
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def _pick_best(address: str, results: list[dict]) -> tuple[tuple[float, float] | None, str]:
    """Choose the exact house among Nominatim's candidates -> ((lat, lng) | None, reason if None).

    Precision rules (the pin must be on the house the address names):
    1. The candidate's house number must match the requested one; street-level hits are rejected.
    2. With a postal code only candidates of that postcode count; without one, the postcode group
       nearest to the depot wins (the planner's couriers work around it).
    3. Only map POINTS count (buildings/areas have no exact spot). OSM address points are preferred
       over shops and bars; the chosen points must agree within settings.GEOCODE_MAX_ERROR_M (2 m),
       otherwise the address fails with a reason instead of getting a pin that may be off.
    """
    requested = requested_house_number(address)
    if not requested:
        return None, "No house number in the address"
    zip_code = extract_postal_code(address)

    matches = []
    for r in results:
        try:
            lat, lng = float(r["lat"]), float(r["lon"])
        except (KeyError, ValueError):
            continue
        addr = r.get("address") or {}
        if in_budapest(lat, lng) and _house_matches(requested, addr.get("house_number")):
            matches.append((lat, lng, addr.get("postcode"), r))
    if not matches:
        return None, f"Street found, but not house number {requested}"

    if zip_code:
        matches = [m for m in matches if m[2] in (zip_code, None)]
        if not matches:
            return None, f"House number {requested} not found in postal code {zip_code}"
        group = matches
    else:
        groups: dict = {}
        for m in matches:
            groups.setdefault(m[2], []).append(m)
        group = min(groups.values(), key=lambda g: min(haversine_km(DEPOT, m[:2]) for m in g))

    max_err = settings.GEOCODE_MAX_ERROR_M
    points = [m for m in group if (_extent_m(m[3]) or 0) <= POINT_EXTENT_M]
    if not points:
        extent = min(_extent_m(m[3]) for m in group)
        return None, f"House {requested} is only mapped as a building/area (about {extent:.0f} m), not as a point"
    address_points = [m for m in points if _is_address_point(m[3])]
    chosen = address_points or points
    lat, lng = _median([m[0] for m in chosen]), _median([m[1] for m in chosen])
    spread_m = max(haversine_km((lat, lng), m[:2]) for m in chosen) * 1000
    if spread_m > max_err:
        return None, (f"House {requested}: {len(chosen)} map points up to {spread_m:.0f} m apart (limit {max_err:g} m)")
    return (lat, lng), ""


_state = threading.local()


def last_failure_reason() -> str:
    """Why the last geocode_address() call on this thread returned None ('' if it succeeded)."""
    return getattr(_state, "reason", "") or "Address not found"


def geocode_address(address: str) -> tuple[float, float] | None:
    """
    Geocode a single address via Nominatim.
    Returns (lat, lng) or None if not found.
    In E2E mock mode, returns deterministic fake coordinates.
    """
    _state.reason = ""
    if settings.E2E_MOCK:
        # Deterministic miss for e2e: a city-less address marked 'nocity' is not found,
        # exactly like a real recipient forgetting the city. Appending the city fixes it.
        lowered = address.lower()
        if "nocity" in lowered and "budapest" not in lowered:
            return None
        return _mock_geocode(address)

    coords, reason = _geocode_real(address)
    _state.reason = reason
    return coords


def _geocode_real(address: str) -> tuple[tuple[float, float] | None, str]:
    _rate_limit()

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": address,
                "format": "jsonv2",
                "limit": 5,
                "addressdetails": 1,
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
            return None, "Address not found"

        coords, reason = _pick_best(address, results)
        if coords is None:
            logger.warning("Nominatim: %s (%s)", reason, address)
        return coords, reason

    except requests.RequestException as e:
        logger.error("Nominatim request failed for '%s': %s", address, e)
        return None, "Geocoding service unavailable"
    except (KeyError, ValueError, IndexError) as e:
        logger.error("Nominatim response parse error for '%s': %s", address, e)
        return None, "Geocoding response could not be read"
