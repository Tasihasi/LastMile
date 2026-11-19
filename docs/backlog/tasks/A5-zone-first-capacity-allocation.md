# A5 — Zone-first, time-capacity-aware allocation

**Email §1** · **P1** · **Depends on:** A2, B1, B2 · **Size:** L

## Goal
Gergő's ordered logic, step 1: *first try to distribute whole **zones** (16) among routes so each route's available time is filled as fully as possible, keeping each route geographically compact around the depot (Orczy út 45).* A zone is the preferred atomic unit; a zip is the minimum atomic unit (A2).

## Context
- Capacity of a route = `(depot_return − depot_start)` × (1 + overrun 7.5 %) (B1/B2). Load of a set of stops = `n × service_time × biker_multiplier + estimated travel time depot→…→depot + breaks` (B2 estimator).
- Zones from A1. Algorithm choice from A0 spike report.

## Scope
- `allocate_zones(stops, bikers[{id, window_minutes, multiplier}], depot, config) -> {assignments: {biker_id: [zone_id…]}, unassigned_zones: [...]}`.
- Heuristic suggestion (confirm against A0): sort zones by load desc; place each in the biker route that minimises added travel time while still fitting capacity; tie-break by geographic proximity (distance of zone centroid to route centroid / depot angle).
- Wire into `cluster_session` when bikers have time windows; otherwise fall back to A2 behaviour.
- Response: per route `{load_minutes, capacity_minutes, zones:[…]}` and top-level `unassigned_zones` (input to A6).

## Acceptance criteria
- **A5-AC1** Every zone placed by this step is entirely in one route (no zone split here).
- **A5-AC2** No route's estimated load exceeds its capacity (incl. 7.5 % overrun allowance) for zones this step assigns.
- **A5-AC3** Zones that fit nowhere are returned in `unassigned_zones`, not silently dropped, not force-fit.
- **A5-AC4** On `REALISTIC_DAY` with feasible parameters, utilisation (Σload/Σcapacity) ≥ 85 % and `unassigned_zones == []`; with deliberately tight parameters `unassigned_zones` non-empty.
- **A5-AC5** Geographic sanity: on a fixture with two far-apart clusters, each cluster's zones land on the same route when capacity allows.
- **A5-AC6** Deterministic; runs < 2 s for 300 stops / 6 bikers.
- **A5-AC7** Biker with a bigger multiplier (B3) receives fewer stops.

## Test plan
- U: `test_zone_allocation.py` — AC1–AC3, AC5–AC7 on pure function with stubbed travel-time estimator.
- A: `SplitPlannerAPITest` — AC4 end-to-end through `/cluster/` with time windows in payload.
- Perf: AC6 simple timing assertion (generous bound).

## Out of scope
Splitting unassigned zones (A6), UI beyond showing load/capacity per route (small badge ok).


## Implementation status (2026-11-17)

Backend only: reachable through the API (`assignments[].window_minutes`) until B1 adds a window input to the wizard. After the verification report: allocation packs to the window (overrun only as flagged overflow), mixed window/lock payloads are rejected, unused bikers get no empty route, and A6 search is branch-and-bound (`split_exact`).
