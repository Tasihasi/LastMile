"""Budapest geography shared by the geocoder, the optimizer and the time model.

Pure data + small geometry helpers, no Django imports.
"""

import math

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

# Everything the app plans lies inside this box (south, west, north, east); a coordinate outside it is a
# wrong geocoder hit (another city, another country), never a real Budapest delivery.
BBOX = (47.33, 18.90, 47.66, 19.36)


def in_budapest(lat, lng):
    return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lng <= BBOX[3]


def haversine_km(a, b):
    """Great-circle distance in km between two (lat, lng) points."""
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 12742.0 * math.asin(math.sqrt(h))
