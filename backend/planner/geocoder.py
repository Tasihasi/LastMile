import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from django.conf import settings

from .addressparse.data import settlement_for_zip
from .budapest import ZIP_CENTROIDS
from .districts import extract_postal_code

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
GOOGLE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
USER_AGENT = "DeliveryPlannerDemo/1.0 (lastmile-c07a.onrender.com)"

CITY_CENTRE = (47.4979, 19.0402)
MOCK_JITTER_DEG = 0.004  # ~400 m

_rate_lock = threading.Lock()
_next_slot = 0.0


class GeocodeError(Exception):
    """A provider could not answer (timeout, HTTP error, quota). Different from "address not found"."""


@dataclass
class GeocodeQuery:
    """What a provider is asked. ``text`` always works; the structured fields are used when present."""

    text: str
    street: str = ""  # street + house number, e.g. "Kazinczy utca 14"
    city: str = ""
    postalcode: str = ""


@dataclass
class GeocodeResult:
    lat: float
    lng: float
    confidence: float | None = None
    matched_address: str = ""
    partial: bool = False


def _nominatim_url() -> str:
    return getattr(settings, "NOMINATIM_URL", "") or NOMINATIM_URL


def _min_interval() -> float:
    """The public Nominatim server allows 1 request/s in total; a self-hosted one is not limited."""
    configured = getattr(settings, "NOMINATIM_MIN_INTERVAL", None)
    if configured not in (None, ""):
        return float(configured)
    return 1.0 if urlparse(_nominatim_url()).hostname == "nominatim.openstreetmap.org" else 0.0


def _rate_limit():
    """Reserve the next request slot, shared by all worker threads (1 request per second on the public server)."""
    global _next_slot
    interval = _min_interval()
    if interval <= 0:
        return
    with _rate_lock:
        now = time.monotonic()
        wait = max(0.0, _next_slot - now)
        _next_slot = max(now, _next_slot) + interval
    if wait > 0:
        time.sleep(wait)


def _mock_geocode(address: str) -> tuple[float, float]:
    """Offline stand-in (E2E_MOCK only): the address lands in its own postal code's area, deterministically."""
    h = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
    zip_code = extract_postal_code(address) or ""
    centre = ZIP_CENTROIDS.get(zip_code)
    if centre is None:
        town = settlement_for_zip(zip_code)
        centre = (town.lat, town.lng) if town is not None and town.key != "budapest" else CITY_CENTRE
    lat0, lng0 = centre
    lat = lat0 + ((h % 2000) / 2000 - 0.5) * 2 * MOCK_JITTER_DEG
    lng = lng0 + (((h >> 16) % 2000) / 2000 - 0.5) * 2 * MOCK_JITTER_DEG
    return (lat, lng)


class MockProvider:
    """Offline provider for E2E_MOCK. 'nocity' = not found unless the address names Budapest;
    'nowhere' = not found unless the address ends with 'Budapest' (what the wizard's bulk retry appends)."""

    name = "mock"

    def geocode(self, query: GeocodeQuery) -> GeocodeResult | None:
        lowered = query.text.lower()
        if "nocity" in lowered and "budapest" not in lowered:
            return None
        if "nowhere" in lowered and not lowered.rstrip().endswith("budapest"):
            return None
        lat, lng = _mock_geocode(query.text)
        return GeocodeResult(lat, lng, confidence=0.5, matched_address=query.text)


class NominatimProvider:
    name = "nominatim"

    def geocode(self, query: GeocodeQuery) -> GeocodeResult | None:
        _rate_limit()
        params: dict = {"format": "jsonv2", "limit": 1}
        if query.street and (query.postalcode or query.city):
            params.update({"street": query.street, "country": "Hungary"})
            if query.city:
                params["city"] = query.city
            if query.postalcode:
                params["postalcode"] = query.postalcode
        else:
            params["q"] = query.text
        try:
            response = requests.get(_nominatim_url(), params=params, headers={"User-Agent": USER_AGENT}, timeout=10)
            response.raise_for_status()
            results = response.json()
            if not results:
                logger.warning("Nominatim returned no results for: %s", query.text)
                return None
            hit = results[0]
            importance = hit.get("importance")
            return GeocodeResult(
                float(hit["lat"]),
                float(hit["lon"]),
                confidence=float(importance) if importance is not None else None,
                matched_address=str(hit.get("display_name", "")),
            )
        except requests.RequestException as e:
            logger.error("Nominatim request failed for '%s': %s", query.text, e)
            raise GeocodeError(f"Nominatim request failed: {e}") from e
        except (KeyError, ValueError, IndexError, TypeError) as e:
            logger.error("Nominatim response parse error for '%s': %s", query.text, e)
            raise GeocodeError(f"Nominatim response unreadable: {e}") from e


class GoogleProvider:
    """Google Geocoding API, last resort (stage 4). Only house-level hits are accepted."""

    name = "google"
    ACCEPT = {"ROOFTOP", "RANGE_INTERPOLATED"}

    def __init__(self, api_key: str):
        self.api_key = api_key

    def geocode(self, query: GeocodeQuery) -> GeocodeResult | None:
        components = ["country:HU"]
        if query.postalcode:
            components.append(f"postal_code:{query.postalcode}")
        try:
            response = requests.get(
                GOOGLE_URL,
                params={"address": query.text, "components": "|".join(components), "key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            raise GeocodeError(f"Google request failed: {e}") from e
        status = data.get("status")
        if status == "ZERO_RESULTS":
            return None
        if status != "OK":
            raise GeocodeError(f"Google geocoding status {status}")
        hit = data["results"][0]
        if hit.get("partial_match"):
            return None
        geometry = hit.get("geometry", {})
        if geometry.get("location_type") not in self.ACCEPT:
            return None
        loc = geometry["location"]
        return GeocodeResult(float(loc["lat"]), float(loc["lng"]), matched_address=hit.get("formatted_address", ""))


_REGISTRY: dict = {}


def register_provider(name: str, provider) -> None:
    """Register a provider instance (tests use this to prove the seam; None removes it)."""
    if provider is None:
        _REGISTRY.pop(name, None)
    else:
        _REGISTRY[name] = provider


def known_provider_names() -> set[str]:
    return {"nominatim", "mock", "google"} | set(_REGISTRY)


def get_provider(name: str):
    if name in _REGISTRY:
        return _REGISTRY[name]
    if name == "nominatim":
        return NominatimProvider()
    if name == "mock":
        return MockProvider()
    if name == "google":
        key = getattr(settings, "GOOGLE_GEOCODING_API_KEY", "")
        return GoogleProvider(key) if key else None
    raise ValueError(f"Unknown geocoder provider '{name}'. Known: {sorted(known_provider_names())}")


def primary_provider():
    if settings.E2E_MOCK:
        return _REGISTRY.get("primary") or MockProvider()
    return get_provider(getattr(settings, "GEOCODER_PROVIDER", "nominatim") or "nominatim")


def google_provider():
    """The stage-4 provider, or None (no key configured). Offline in E2E_MOCK unless a test registers one."""
    if settings.E2E_MOCK:
        return _REGISTRY.get("google")
    return get_provider("google")


def geocode(query: GeocodeQuery, provider=None) -> GeocodeResult | None:
    """Geocode with ``provider`` (default: the configured one). Raises GeocodeError when the provider fails."""
    return (provider or primary_provider()).geocode(query)


def geocode_address(address: str) -> tuple[float, float] | None:
    """
    Geocode a single address with the configured provider.
    Returns (lat, lng) or None if not found or the provider failed.
    In E2E mock mode, returns deterministic fake coordinates.
    """
    try:
        result = geocode(GeocodeQuery(text=address))
    except GeocodeError:
        return None
    return (result.lat, result.lng) if result else None
