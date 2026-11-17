"""Deterministic synthetic Budapest data for zone / zip-allocation tests (backlog A0).

Test-only helpers: nothing in production code imports this module.
"""

import random

from ..models import DeliverySession, DeliveryStop

# Approximate (lat, lng) centroid per Budapest postal code. 34 zips, matching the
# size of the real zone sheet; the real zip list is a placeholder until A1 lands.
ZIP_CENTROIDS = {
    "1011": (47.4985, 19.0370),
    "1021": (47.5170, 19.0200),
    "1024": (47.5120, 19.0310),
    "1034": (47.5400, 19.0420),
    "1051": (47.5010, 19.0510),
    "1052": (47.4955, 19.0535),
    "1061": (47.5050, 19.0640),
    "1065": (47.5090, 19.0620),
    "1073": (47.4990, 19.0700),
    "1074": (47.5000, 19.0750),
    "1081": (47.4930, 19.0780),
    "1082": (47.4870, 19.0800),
    "1088": (47.4900, 19.0700),
    "1091": (47.4780, 19.0770),
    "1092": (47.4820, 19.0680),
    "1095": (47.4700, 19.0670),
    "1111": (47.4750, 19.0450),
    "1117": (47.4720, 19.0350),
    "1118": (47.4500, 19.0240),
    "1122": (47.4960, 19.0100),
    "1126": (47.4930, 19.0040),
    "1131": (47.5350, 19.0720),
    "1132": (47.5200, 19.0560),
    "1138": (47.5500, 19.0580),
    "1141": (47.5180, 19.1100),
    "1146": (47.5150, 19.0850),
    "1148": (47.5090, 19.1120),
    "1149": (47.5300, 19.1080),
    "1151": (47.5580, 19.1130),
    "1161": (47.5150, 19.1650),
    "1181": (47.4400, 19.1750),
    "1191": (47.4650, 19.1300),
    "1201": (47.4350, 19.1200),
    "1211": (47.4250, 19.0650),
}

JITTER_DEG = 0.004  # ~400 m; keeps every stop well inside the Budapest bbox

# Uneven density: singletons up to 25 stops, plus one zip (1138) bigger than a
# single route's capacity of 48, to exercise forced zip splitting.
REALISTIC_DAY_ZIP_COUNTS = {
    "1011": 6, "1021": 2, "1024": 4, "1034": 3, "1051": 25, "1052": 9,
    "1061": 11, "1065": 3, "1073": 25, "1074": 7, "1081": 5, "1082": 2,
    "1088": 1, "1091": 4, "1092": 3, "1095": 1, "1111": 8, "1117": 5,
    "1118": 1, "1122": 3, "1126": 2, "1131": 10, "1132": 7, "1138": 56,
    "1141": 4, "1146": 6, "1148": 2, "1149": 1, "1151": 3, "1161": 1,
    "1181": 3, "1191": 2, "1201": 3, "1211": 1,
}  # fmt: skip

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
