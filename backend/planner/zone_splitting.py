"""Minimal zone splitting (backlog A6): place the zones step 1 could not fit, zip by zip.

Only whole zips move (a zip is never split). The plan breaks as few zones as possible; ties go to
the smaller total estimated load (less extra travel). A zip that fits no route's capacity is kept
whole and flagged instead of being forced silently.
"""

import itertools
from collections import defaultdict

from . import timing
from .clustering import stop_zip

# Exhaustive search while routes ** zips stays below this; greedy above it.
EXACT_LIMIT = 5000


def _default_estimator(stops, multiplier, depot):
    return timing.estimate_route_minutes(stops, multiplier=multiplier, depot=depot)


def resolve_unassigned(alloc, bikers, depot=timing.DEPOT, estimator=None, tolerance=timing.OVERRUN_TOLERANCE):
    """Distribute the unassigned zones of `alloc` (from allocate_zones) over the bikers' routes.

    Returns {"routes": {biker_id: {stops, load_minutes, capacity_minutes}},
             "split_zones": [{"zone_id", "parts": [{"zips": [...], "route": biker_id}]}],
             "over_capacity_zips": [zip], "over_capacity_routes": [biker_id]}.
    Every stop of the unassigned zones ends up on exactly one route.
    """
    estimator = estimator or _default_estimator
    ids = [b["id"] for b in bikers]
    mult = {b["id"]: b.get("multiplier") or 1.0 for b in bikers}
    cap = {b["id"]: timing.capacity_minutes(b["window_minutes"], tolerance) for b in bikers}
    base = {bid: list(alloc["routes"][bid]["stops"]) for bid in ids}

    # zip units of the unassigned zones, biggest first (deterministic)
    zips = []  # (zone, zip, stops)
    for zone, stops in alloc["unassigned_stops"].items():
        by_zip = defaultdict(list)
        for s in stops:
            by_zip[stop_zip(s)].append(s)
        for z, group in by_zip.items():
            zips.append((zone, z, group))
    zips.sort(key=lambda t: (-len(t[2]), t[0], t[1]))

    cache = {}

    def load(bid, members):
        key = (bid, tuple(members))
        if key not in cache:
            stops = base[bid] + [s for i in members for s in zips[i][2]]
            cache[key] = estimator(stops, mult[bid], depot) if stops else 0.0
        return cache[key]

    def evaluate(plan):
        """plan[i] = route index for zip i -> (cost tuple, loads)."""
        members = {bid: [] for bid in ids}
        for i, r in enumerate(plan):
            members[ids[r]].append(i)
        loads = {bid: load(bid, m) for bid, m in members.items()}
        over_routes = sum(1 for bid in ids if loads[bid] > cap[bid])
        routes_of = defaultdict(set)
        for i, r in enumerate(plan):
            routes_of[zips[i][0]].add(r)
        broken = sum(1 for rs in routes_of.values() if len(rs) > 1)
        return (over_routes, broken, round(sum(loads.values()), 6), plan), loads

    best = None
    if zips and len(ids) ** len(zips) <= EXACT_LIMIT:
        for plan in itertools.product(range(len(ids)), repeat=len(zips)):
            cost, loads = evaluate(plan)
            if best is None or cost < best[0]:
                best = (cost, loads)
    elif zips:
        plan = []
        members = {bid: [] for bid in ids}
        zone_routes = defaultdict(set)
        for i, (zone, _, _) in enumerate(zips):
            options = []
            for r, bid in enumerate(ids):
                new = load(bid, members[bid] + [i])
                fits = new <= cap[bid]
                options.append(
                    (not fits, r not in zone_routes[zone] and bool(zone_routes[zone]), new - load(bid, members[bid]), r)
                )
            _, _, _, r = min(options)
            plan.append(r)
            members[ids[r]].append(i)
            zone_routes[zone].add(r)
        best = evaluate(tuple(plan))
    else:
        best = ((0, 0, 0.0, ()), {bid: load(bid, []) for bid in ids})

    (_, _, _, plan), loads = best
    routes = {
        bid: {"stops": list(base[bid]), "load_minutes": 0.0, "capacity_minutes": round(cap[bid], 1)} for bid in ids
    }
    placed = defaultdict(lambda: defaultdict(list))  # zone -> route -> zips
    for i, r in enumerate(plan):
        routes[ids[r]]["stops"] += zips[i][2]
        placed[zips[i][0]][ids[r]].append(zips[i][1])
    for bid in ids:
        routes[bid]["load_minutes"] = round(loads[bid], 1)

    over_routes = [bid for bid in ids if loads[bid] > cap[bid]]
    over_zips = sorted({zips[i][1] for i, r in enumerate(plan) if ids[r] in over_routes})
    split = [
        {"zone_id": zone, "parts": [{"zips": sorted(z), "route": bid} for bid, z in parts.items()]}
        for zone, parts in sorted(placed.items())
        if len(parts) > 1
    ]
    return {
        "routes": routes,
        "split_zones": split,
        "over_capacity_zips": over_zips,
        "over_capacity_routes": over_routes,
    }
