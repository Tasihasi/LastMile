"""Consistency guard (Must #2): a geocoder hit must agree with the address's postal code / settlement.

Deliberately lenient: it checks the AREA (zip centroid or settlement radius), never house-number or metre
accuracy, because strict pinning refused about half of real addresses and was reverted (PR #69).
"""

from .addressparse.data import is_budapest_zip, settlement_by_name, settlement_for_zip
from .budapest import ZIP_CENTROIDS, haversine_km

ZIP_RADIUS_KM = 3.0  # Budapest zips of districts V-IX are well inside this
BUDAPEST_BBOX = (47.33, 47.65, 18.90, 19.40)  # lat_min, lat_max, lng_min, lng_max


def _in_budapest(lat: float, lng: float) -> bool:
    return BUDAPEST_BBOX[0] <= lat <= BUDAPEST_BBOX[1] and BUDAPEST_BBOX[2] <= lng <= BUDAPEST_BBOX[3]


def check(lat: float, lng: float, zip_code: str = "", city: str = "") -> tuple[bool, str]:
    """(consistent, reason). Unknown zip/settlement cannot be judged, so it passes."""
    zip_code = zip_code or ""
    centre = ZIP_CENTROIDS.get(zip_code)
    if centre is not None:
        km = haversine_km((lat, lng), centre)
        if km > ZIP_RADIUS_KM:
            return False, f"{km:.1f} km from postal code {zip_code}"
        return True, ""
    town = settlement_for_zip(zip_code) or (settlement_by_name(city) if city else None)
    if town is None:
        return True, ""
    if is_budapest_zip(zip_code) or town.key == "budapest":
        if not _in_budapest(lat, lng):
            return False, f"outside Budapest (postal code {zip_code or '?'})"
        return True, ""
    km = haversine_km((lat, lng), (town.lat, town.lng))
    if km > town.radius_km:
        return False, f"{km:.0f} km from {town.name}"
    return True, ""
