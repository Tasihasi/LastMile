# B2 — Route duration estimate + 7.5 % overrun status

**Email §2** · **P1** · **Depends on:** B1 · **Size:** M

## Goal
For each route show: estimated total time vs. available window, with status **OK**, **OVERTIME** (exceeds window by ≤ 7.5 % → dispatcher must ask the biker if overtime is fine), **INFEASIBLE** (> 7.5 %). The planner is responsible for realistic parameters; the tool just tells the truth.

## Scope
- `estimate_route_minutes(stops, service_min, multiplier=1.0, travel_minutes=None, break_min)` in `timing.py`:
  `= n × service × multiplier + travel + break`, where `travel` = optimizer `total_duration` if the route is optimized, else a heuristic estimate (nearest-neighbour length / avg speed — keep simple and documented).
- `route_status(estimated, available) -> ok | overtime | infeasible`.
- Serializer fields: `estimated_minutes`, `available_minutes`, `time_status`, `overrun_pct`.
- UI badge on each route card (green / amber "Túlóra egyeztetés" / red).

## Acceptance criteria
- **B2-AC1** est ≤ available → `ok`, `overrun_pct == 0`.
- **B2-AC2** est = available × 1.075 exactly → `overtime` (boundary inclusive); × 1.0751 → `infeasible`.
- **B2-AC3** No `depot_*` times → `time_status = null`, no badge (backwards compatible).
- **B2-AC4** After optimization, estimate uses real ORS duration; before, the heuristic. Both paths covered.
- **B2-AC5** Moving a stop (move-stop / move-zip) changes the estimate in the next response.
- **B2-AC6** Amber badge text tells the dispatcher to confirm overtime with the biker.

## Test plan
- U: `test_timing.py` — AC1, AC2 (boundary table), AC3, AC4 (stub optimizer total_duration).
- A: AC5 — move a stop, compare `estimated_minutes` before/after.
- E: `route-wizard.spec.ts` or `clustering.spec.ts` — tight window shows amber/red badge (AC6).

## Out of scope
Auto-allocation (A5 consumes `estimate_route_minutes`), per-route service time (B4).
