import math
import random

import requests
from django.conf import settings

ORS_BASE = "https://api.openrouteservice.org"


def _get_headers():
    return {
        "Authorization": settings.ORS_API_KEY,
        "Content-Type": "application/json",
    }


def _mock_optimize(stops, depot=None) -> list[int]:
    """Sort stops by angle from centroid for a reasonable-looking route order."""
    if len(stops) < 2:
        return [s.id for s in stops]

    avg_lat = sum(s.lat for s in stops) / len(stops)
    avg_lng = sum(s.lng for s in stops) / len(stops)

    def angle(s):
        return math.atan2(s.lat - avg_lat, s.lng - avg_lng)

    sorted_stops = sorted(stops, key=angle)
    return [s.id for s in sorted_stops]


def _mock_route_details(ordered_stops, depot=None) -> dict | None:
    """Generate fake but structurally valid route geometry and segments."""
    if len(ordered_stops) < 2 and not depot:
        return None

    coordinates = []
    if depot:
        coordinates.append([depot[1], depot[0]])
    coordinates.extend([[s.lng, s.lat] for s in ordered_stops])
    if depot:
        coordinates.append([depot[1], depot[0]])

    geometry = {"type": "LineString", "coordinates": coordinates}

    segments = []
    for i in range(len(coordinates) - 1):
        segments.append(
            {
                "from_index": i,
                "to_index": i + 1,
                "duration": random.randint(120, 600),
                "distance": random.randint(500, 3000),
            }
        )

    return {
        "geometry": geometry,
        "segments": segments,
        "total_duration": sum(s["duration"] for s in segments),
        "total_distance": sum(s["distance"] for s in segments),
    }


def optimize_route(stops, depot=None) -> list[int]:
    """Return stop IDs in ORS-optimized travel order via the VROOM endpoint.

    `depot` is an optional `(lat, lng)` tuple anchoring the route's start
    and end. In E2E mock mode (`settings.E2E_MOCK`), returns an
    angle-sorted approximation without contacting ORS so tests stay
    hermetic.
    """
    if settings.E2E_MOCK:
        return _mock_optimize(stops, depot)

    if len(stops) < 2:
        return [s.id for s in stops]

    if depot:
        start_end = [depot[1], depot[0]]  # [lng, lat] for ORS
    else:
        first = stops[0]
        start_end = [first.lng, first.lat]

    body = {
        "jobs": [{"id": stop.id, "location": [stop.lng, stop.lat]} for stop in stops],
        "vehicles": [
            {
                "id": 1,
                "profile": "driving-car",
                "start": start_end,
                "end": start_end,
            }
        ],
    }

    response = requests.post(
        f"{ORS_BASE}/optimization",
        json=body,
        headers=_get_headers(),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    ordered_ids = []
    for step in data["routes"][0]["steps"]:
        if step["type"] == "job":
            ordered_ids.append(step["job"])

    return ordered_ids


def get_route_details(ordered_stops, depot=None) -> dict | None:
    """Return road-following geometry plus per-segment timing for the ordered stops.

    `depot` is an optional `(lat, lng)` tuple. When set, the route starts
    and ends at the depot; otherwise it starts and ends at the first and
    last stops. In E2E mock mode (`settings.E2E_MOCK`), returns
    straight-line geometry instead of calling ORS so tests stay hermetic.
    """
    if settings.E2E_MOCK:
        return _mock_route_details(ordered_stops, depot)

    if len(ordered_stops) < 2 and not depot:
        return None

    coordinates = []
    if depot:
        coordinates.append([depot[1], depot[0]])  # [lng, lat]
    coordinates.extend([[s.lng, s.lat] for s in ordered_stops])
    if depot:
        coordinates.append([depot[1], depot[0]])

    response = requests.post(
        f"{ORS_BASE}/v2/directions/driving-car/geojson",
        json={"coordinates": coordinates},
        headers=_get_headers(),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    feature = data["features"][0]
    geometry = feature["geometry"]
    segments = feature["properties"]["segments"]

    route_segments = []
    for i, seg in enumerate(segments):
        route_segments.append(
            {
                "from_index": i,
                "to_index": i + 1,
                "duration": round(seg["duration"]),
                "distance": round(seg["distance"]),
            }
        )

    total_duration = round(sum(s["duration"] for s in segments))
    total_distance = round(sum(s["distance"] for s in segments))

    return {
        "geometry": geometry,
        "segments": route_segments,
        "total_duration": total_duration,
        "total_distance": total_distance,
    }
