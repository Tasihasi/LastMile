"""Zone-first allocation (backlog A5): hand whole zones to bikers, filling each one's time window.

A zone (planner/zones.json) is the preferred atomic unit. Zips that belong to no zone are their
own unit ("zip:1111") so nothing is dropped. Stops without a postal code are not allocated here.
"""

import math
from collections import defaultdict

from . import timing, zones
from .clustering import stop_zip


def _centroid(stops):
    return (sum(s.lat for s in stops) / len(stops), sum(s.lng for s in stops) / len(stops))


def zone_units(stops):
    """{unit_id: [stops]} with unit_id = zone id, or "zip:<zip>" for zips outside the zone config."""
    units = defaultdict(list)
    for stop in stops:
        z = stop_zip(stop)
        if not z:
            continue
        units[zones.zone_for_zip(z) or f"zip:{z}"].append(stop)
    return dict(units)


def allocate_zones(stops, bikers, depot=timing.DEPOT, estimator=None, tolerance=timing.OVERRUN_TOLERANCE):
    """Place whole zones on bikers without exceeding any biker's time window.

    bikers: list of {"id", "window_minutes", "multiplier" (optional, default 1.0)}.
    estimator(stops, multiplier, depot) -> minutes; defaults to timing.estimate_route_minutes.

    Zones go in by descending load. Each one is placed on the biker whose route grows the least
    (shortest detour) among those it still fits; ties go to the nearer route centroid, then to the
    earlier biker. A zone that fits nowhere is returned in `unassigned_zones` (never force-fit,
    never split here). Deterministic.

    Returns {"assignments": {biker_id: [zone_id]}, "routes": {biker_id: {load_minutes,
    capacity_minutes, zones, stops}}, "unassigned_zones": [{"zone", "stop_count", "load_minutes"}]}.
    """
    if estimator is None:

        def estimator(route_stops, multiplier, depot):
            return timing.estimate_route_minutes(route_stops, multiplier=multiplier, depot=depot)

    units = zone_units(stops)
    solo = {u: estimator(s, 1.0, depot) for u, s in units.items()}
    order = sorted(units, key=lambda u: (-solo[u], u))

    state = {
        b["id"]: {"stops": [], "zones": [], "load": 0.0, "cap": timing.capacity_minutes(b["window_minutes"], tolerance)}
        for b in bikers
    }
    mult = {b["id"]: b.get("multiplier") or 1.0 for b in bikers}
    unassigned = []

    for unit in order:
        best = None
        for b in bikers:
            bid = b["id"]
            st = state[bid]
            new_load = estimator(st["stops"] + units[unit], mult[bid], depot)
            if new_load > st["cap"]:
                continue
            added = new_load - st["load"]
            dist = math.dist(_centroid(st["stops"]), _centroid(units[unit])) if st["stops"] else math.inf
            key = (round(added, 6), dist if st["stops"] else math.inf)
            if best is None or key < best[0]:
                best = (key, bid, new_load)
        if best is None:
            unassigned.append({"zone": unit, "stop_count": len(units[unit]), "load_minutes": round(solo[unit], 1)})
            continue
        _, bid, new_load = best
        state[bid]["stops"] += units[unit]
        state[bid]["zones"].append(unit)
        state[bid]["load"] = new_load

    return {
        "assignments": {bid: st["zones"] for bid, st in state.items()},
        "routes": {
            bid: {
                "load_minutes": round(st["load"], 1),
                "capacity_minutes": round(st["cap"], 1),
                "zones": st["zones"],
                "stops": st["stops"],
            }
            for bid, st in state.items()
        },
        "unassigned_zones": unassigned,
        "unassigned_stops": {u["zone"]: units[u["zone"]] for u in unassigned},
    }
