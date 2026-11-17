"""Time model for route planning: one place to edit the global constants.

Service time, travel speed, break and the overrun tolerance are constants in code (no UI yet).
Backlog B1/B2 extend this module (depot times, status badges); A5 only needs the estimator.
"""

import math

import numpy as np

SERVICE_TIME_PER_STOP_MIN = 2.0  # minutes spent at each address
AVG_SPEED_KMH = 15.0  # door-to-door average of a courier in the inner city
BREAK_MIN = 20.0  # one break per route
OVERRUN_TOLERANCE = 0.075  # a route may exceed its window by 7.5 %

# Depot: Orczy út 45, Budapest (approximate coordinates).
DEPOT = (47.4893, 19.0760)

_KM_PER_DEG_LAT = 111.2


def _km_matrix(points):
    pts = np.asarray(points, dtype=float)
    lat0 = math.radians(pts[:, 0].mean())
    xy = np.column_stack([pts[:, 0] * _KM_PER_DEG_LAT, pts[:, 1] * _KM_PER_DEG_LAT * math.cos(lat0)])
    diff = xy[:, None, :] - xy[None, :, :]
    return np.sqrt((diff**2).sum(axis=2))


def tour_km(points, depot=DEPOT):
    """Length (km) of a nearest-neighbour tour depot -> points -> depot (heuristic, deterministic)."""
    if not points:
        return 0.0
    dist = _km_matrix([depot, *points])
    n = len(points)
    visited = np.zeros(n + 1, dtype=bool)
    visited[0] = True
    cur, total = 0, 0.0
    for _ in range(n):
        d = np.where(visited, np.inf, dist[cur])
        nxt = int(np.argmin(d))
        total += float(d[nxt])
        visited[nxt] = True
        cur = nxt
    return total + float(dist[cur, 0])


def estimate_route_minutes(
    stops,
    service_min=SERVICE_TIME_PER_STOP_MIN,
    multiplier=1.0,
    break_min=BREAK_MIN,
    depot=DEPOT,
    travel_minutes=None,
):
    """n x service x multiplier + travel + break. Empty route = 0.

    `travel_minutes` (e.g. the optimizer's total_duration) wins over the heuristic tour estimate.
    """
    stops = list(stops)
    if not stops:
        return 0.0
    if travel_minutes is None:
        travel_minutes = tour_km([(s.lat, s.lng) for s in stops], depot) / AVG_SPEED_KMH * 60
    return len(stops) * service_min * multiplier + travel_minutes + break_min


def capacity_minutes(window_minutes, tolerance=OVERRUN_TOLERANCE):
    return window_minutes * (1 + tolerance)
