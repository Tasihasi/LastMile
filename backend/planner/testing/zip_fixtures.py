"""Deterministic synthetic Budapest data for zone / zip-allocation tests (backlog A0).

Test-only helpers: nothing in production code imports this module.
"""

import random

from ..models import DeliverySession, DeliveryStop

# Approximate (lat, lng) centroid per postal code: the 34 zips of districts V-IX that the zone
# sheet covers (same zips as planner/zones.json).
ZIP_CENTROIDS = {
    "1051": (47.499, 19.05),
    "1052": (47.495, 19.053),
    "1053": (47.493, 19.056),
    "1054": (47.504, 19.048),
    "1055": (47.513, 19.046),
    "1056": (47.49, 19.05),
    "1061": (47.504, 19.062),
    "1062": (47.509, 19.064),
    "1063": (47.513, 19.068),
    "1064": (47.511, 19.06),
    "1065": (47.506, 19.059),
    "1066": (47.507, 19.054),
    "1067": (47.51, 19.07),
    "1068": (47.51, 19.078),
    "1071": (47.507, 19.078),
    "1072": (47.5, 19.069),
    "1073": (47.504, 19.072),
    "1074": (47.5, 19.079),
    "1075": (47.499, 19.071),
    "1076": (47.498, 19.083),
    "1077": (47.496, 19.077),
    "1078": (47.509, 19.083),
    "1081": (47.495, 19.08),
    "1082": (47.488, 19.077),
    "1083": (47.486, 19.085),
    "1084": (47.493, 19.087),
    "1085": (47.49, 19.069),
    "1086": (47.49, 19.09),
    "1088": (47.493, 19.066),
    "1089": (47.487, 19.097),
    "1092": (47.482, 19.07),
    "1093": (47.478, 19.076),
    "1094": (47.47, 19.084),
    "1096": (47.462, 19.1),
}

JITTER_DEG = 0.004  # ~400 m; keeps every stop well inside the Budapest bbox

# Shaped like the real 2026-11-17 day (counts scaled to ~30 %): singletons up to ~16 stops, plus
# one zip (1054) bigger than a single route's capacity of 48, to exercise forced zip splitting.
REALISTIC_DAY_ZIP_COUNTS = {
    "1051": 10,
    "1052": 8,
    "1053": 5,
    "1054": 56,
    "1055": 14,
    "1056": 4,
    "1061": 4,
    "1062": 5,
    "1063": 4,
    "1064": 6,
    "1065": 8,
    "1066": 6,
    "1067": 5,
    "1068": 5,
    "1071": 8,
    "1072": 5,
    "1073": 5,
    "1074": 9,
    "1075": 4,
    "1076": 5,
    "1077": 11,
    "1078": 6,
    "1081": 3,
    "1082": 3,
    "1083": 5,
    "1084": 3,
    "1085": 3,
    "1086": 3,
    "1088": 2,
    "1089": 3,
    "1092": 2,
    "1093": 3,
    "1094": 6,
    "1096": 2,
}

REALISTIC_DAY = {
    "zip_counts": REALISTIC_DAY_ZIP_COUNTS,
    "bikers": ["biker_1", "biker_2", "biker_3", "biker_4"],
}


def make_stops(zip_counts, seed=42):
    """Return unsaved DeliveryStop objects, `zip_counts[zip]` of them per zip.

    Deterministic: the same (zip_counts, seed) always yields identical names,
    coordinates and postal codes.
    """
    rng = random.Random(seed)
    stops = []
    for postal_code in sorted(zip_counts):
        lat0, lng0 = ZIP_CENTROIDS[postal_code]
        for _ in range(zip_counts[postal_code]):
            n = len(stops) + 1
            stops.append(
                DeliveryStop(
                    name=f"Stop {n:03d}",
                    raw_address=f"{postal_code} Budapest, Teszt utca {n}",
                    postal_code=postal_code,
                    lat=round(lat0 + rng.uniform(-JITTER_DEG, JITTER_DEG), 6),
                    lng=round(lng0 + rng.uniform(-JITTER_DEG, JITTER_DEG), 6),
                    geocode_status=DeliveryStop.GeocodeStatus.SUCCESS,
                )
            )
    return stops


def make_session(owner=None, zip_counts=None, seed=42, name="Fixture day"):
    """Persist a DeliverySession with generated stops; returns the session."""
    if zip_counts is None:
        zip_counts = REALISTIC_DAY_ZIP_COUNTS
    session = DeliverySession.objects.create(owner=owner, name=name)
    stops = make_stops(zip_counts, seed=seed)
    for stop in stops:
        stop.session = session
    DeliveryStop.objects.bulk_create(stops)
    return session
