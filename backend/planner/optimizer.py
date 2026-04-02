import requests
from django.conf import settings

ORS_BASE = "https://api.openrouteservice.org"


def _get_headers():
    return {
        "Authorization": settings.ORS_API_KEY,
        "Content-Type": "application/json",
    }


def optimize_route(stops) -> list[int]:
    """
    Call ORS optimization (VROOM) to get optimal stop order.
    Returns list of stop IDs in optimized order.
    """
    if len(stops) < 2:
        return [s.id for s in stops]

    first = stops[0]

    body = {
        "jobs": [{"id": stop.id, "location": [stop.lng, stop.lat]} for stop in stops],
        "vehicles": [
            {
                "id": 1,
                "profile": "driving-car",
                "start": [first.lng, first.lat],
                "end": [first.lng, first.lat],
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


def get_route_geometry(ordered_stops) -> dict | None:
    """
    Call ORS directions to get the actual road route as GeoJSON.
    Returns GeoJSON LineString geometry or None.
    """
    if len(ordered_stops) < 2:
        return None

    coordinates = [[s.lng, s.lat] for s in ordered_stops]

    response = requests.post(
        f"{ORS_BASE}/v2/directions/driving-car/geojson",
        json={"coordinates": coordinates},
        headers=_get_headers(),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return data["features"][0]["geometry"]
