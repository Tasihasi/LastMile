"""Minimal zone splitting (backlog A6): place the zones step 1 could not fit, zip by zip.

Only whole zips move (a zip is never split). The plan breaks as few zones as possible; ties go to
the smaller total estimated load (less extra travel). A zip that fits no route's capacity is kept
whole and flagged instead of being forced silently.
"""

from collections import defaultdict

from . import timing
from .clustering import stop_zip

# Branch-and-bound budget (search nodes). Within it the result is provably optimal; beyond it the
# best plan found so far is returned and `exact` is False.
NODE_LIMIT = 30000


def _over(loads, caps):
    """Total minutes by which routes exceed their caps (0 when every route fits)."""
    return round(sum(max(0.0, load - caps[bid]) for bid, load in loads.items()), 6)


def _default_estimator(stops, multiplier, depot):
    return timing.estimate_route_minutes(stops, multiplier=multiplier, depot=depot)


def resolve_unassigned(alloc, bikers, depot=timing.DEPOT, estimator=None, tolerance=timing.OVERRUN_TOLERANCE):
    """Distribute the unassigned zones of `alloc` (from allocate_zones) over the bikers' routes.

    Returns {"routes": {biker_id: {stops, load_minutes, capacity_minutes}},
             "split_zones": [{"zone_id", "parts": [{"zips": [...], "route": biker_id}]}],
             "over_capacity_zips": [zip], "over_capacity_routes": [biker_id]}.
    The window is the target; the tolerance is only used as overflow (cost order: minutes past the
    tolerance, minutes past the window, zones broken, total load). Every stop of the unassigned zones
    ends up on exactly one route. `exact` is False only if the search budget ran out.
    """
    estimator = estimator or _default_estimator
    ids = [b["id"] for b in bikers]
    mult = {b["id"]: b.get("multiplier") or 1.0 for b in bikers}
    soft = {b["id"]: timing.capacity_minutes(b["window_minutes"], 0) for b in bikers}  # the window itself
    hard = {b["id"]: timing.capacity_minutes(b["window_minutes"], tolerance) for b in bikers}  # + overrun
    cap = soft
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
        routes_of = defaultdict(set)
        for i, r in enumerate(plan):
            routes_of[zips[i][0]].add(r)
        broken = sum(1 for rs in routes_of.values() if len(rs) > 1)
        return (_over(loads, hard), _over(loads, soft), broken, round(sum(loads.values()), 6), plan), loads

    def greedy():
        plan = []
        members = {bid: [] for bid in ids}
        zone_routes = defaultdict(set)
        for i, (zone, _, _) in enumerate(zips):
            options = []
            for r, bid in enumerate(ids):
                new = load(bid, members[bid] + [i])
                options.append(
                    (
                        new > soft[bid],
                        r not in zone_routes[zone] and bool(zone_routes[zone]),
                        new - load(bid, members[bid]),
                        r,
                    )
                )
            r = min(options)[3]
            plan.append(r)
            members[ids[r]].append(i)
            zone_routes[zone].add(r)
        return tuple(plan)

    exact = True
    if not zips:
        best = ((0, 0, 0, 0.0, ()), {bid: load(bid, []) for bid in ids})
    else:
        # Branch and bound: start from the greedy plan, prune any partial plan that already costs
        # at least as much (loads only grow as zips are added). Bounded by NODE_LIMIT.
        best = evaluate(greedy())
        members = [[] for _ in ids]
        loads = [load(bid, []) for bid in ids]
        zone_routes = defaultdict(set)
        plan = []
        nodes = 0

        def partial_cost(broken):
            d = dict(zip(ids, loads, strict=True))
            return (_over(d, hard), _over(d, soft), broken, round(sum(loads), 6))

        def search(i, broken):
            nonlocal best, exact, nodes
            nodes += 1
            if nodes > NODE_LIMIT:
                exact = False
                return
            cost = partial_cost(broken)
            if cost >= best[0][:4]:
                return
            if i == len(zips):
                best = (cost + (tuple(plan),), dict(zip(ids, loads, strict=True)))
                return
            zone = zips[i][0]
            order = sorted(
                range(len(ids)),
                key=lambda r: (
                    load(ids[r], members[r] + [i]) > soft[ids[r]],
                    r not in zone_routes[zone] and bool(zone_routes[zone]),
                    load(ids[r], members[r] + [i]) - loads[r],
                    r,
                ),
            )
            for r in order:
                old = loads[r]
                new_broken = broken + (
                    1 if zone_routes[zone] and r not in zone_routes[zone] and len(zone_routes[zone]) == 1 else 0
                )
                added = r not in zone_routes[zone]
                members[r].append(i)
                loads[r] = load(ids[r], members[r])
                if added:
                    zone_routes[zone].add(r)
                plan.append(r)
                search(i + 1, new_broken)
                plan.pop()
                if added:
                    zone_routes[zone].discard(r)
                members[r].pop()
                loads[r] = old

        search(0, 0)

    plan, loads = best[0][4], best[1]
    routes = {
        bid: {"stops": list(base[bid]), "load_minutes": 0.0, "capacity_minutes": round(cap[bid], 1)} for bid in ids
    }
    placed = defaultdict(lambda: defaultdict(list))  # zone -> route -> zips
    for i, r in enumerate(plan):
        routes[ids[r]]["stops"] += zips[i][2]
        placed[zips[i][0]][ids[r]].append(zips[i][1])
    for bid in ids:
        routes[bid]["load_minutes"] = round(loads[bid], 1)

    over_routes = [bid for bid in ids if loads[bid] > hard[bid]]
    overrun_routes = [bid for bid in ids if soft[bid] < loads[bid] <= hard[bid]]
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
        "overrun_routes": overrun_routes,  # within the tolerance, but past the window
        "exact": exact,
    }
