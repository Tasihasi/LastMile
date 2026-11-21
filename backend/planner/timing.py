"""Time model for route planning: one place to edit the global constants.

Service time, travel speed, break and the overrun tolerance are constants in code (no UI yet).
Backlog B1/B2 extend this module (depot times, status badges); A5 only needs the estimator.
"""

from . import tsp
from .budapest import haversine_km

SERVICE_TIME_PER_STOP_MIN = 2.0  # minutes spent at each address
AVG_SPEED_KMH = 15.0  # door-to-door average of a courier in the inner city
BREAK_MIN = 20.0  # one break per route
OVERRUN_TOLERANCE = 0.075  # a route may exceed its window by 7.5 %

# Depot: Orczy út 45, Budapest (approximate coordinates).
DEPOT = (47.4893, 19.0760)


def tour_km(points, depot=DEPOT):
    """Length (km) of a short closed tour depot -> points -> depot.

    The visiting order is optimized (nearest neighbour + 2-opt), not the file order. Straight-line
    length; street detours are already inside AVG_SPEED_KMH (door-to-door). Deterministic.
    """
    if not points:
        return 0.0
    order = tsp.optimize_order(list(points), depot)
    path = [depot, *(points[i] for i in order), depot]
    return sum(haversine_km(a, b) for a, b in zip(path, path[1:], strict=False))


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
