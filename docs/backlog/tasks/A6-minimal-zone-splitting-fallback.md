# A6 — Minimal zone-splitting fallback

**Email §1** · **P1** · **Depends on:** A5 · **Size:** M

## Goal
Step 2 of Gergő's logic: if some zones are unassigned although *total* free time suffices, break up **as few zones as necessary**, moving **whole zips** (never single stops) into other routes. Geography stays important.

## Scope
- `resolve_unassigned(unassigned_zones, partial_allocation, ...)`: for each unassigned zone, try zip-level placement; choose the plan that **minimises the number of zones broken** (primary) and then extra travel time (secondary).
- If a single zip alone exceeds every route's capacity → leave it whole in the least-loaded route, mark `over_capacity_zips` (planner decides; A2 rule: zip is never split).
- Response adds `split_zones: [{zone_id, parts:[{zips, route}]}]` so the UI can show what was broken.

## Acceptance criteria
- **A6-AC1** Output satisfies zip integrity (A2-AC1) — zero `zip_conflicts`.
- **A6-AC2** Every stop assigned; none dropped.
- **A6-AC3** Fixture where only 1 zone must break (hand-built) → `len(split_zones) == 1`. Fixture solvable without breaking → `split_zones == []`.
- **A6-AC4** Route loads respect capacity + 7.5 % wherever mathematically possible; otherwise the offending route is flagged (`over_capacity`) and the rest still respect it.
- **A6-AC5** Brute-force check on small instances (≤5 zones, ≤3 routes): number of broken zones equals the brute-force minimum.
- **A6-AC6** UI review view labels split zones ("Zóna Z07 szétbontva: 1082→Route_1, 1083→Route_2").

## Test plan
- U: `test_zone_splitting.py` — AC1–AC5 (AC5 enumerates all assignments in the test, tiny sizes).
- A: through `/cluster/` — AC1, AC2, AC4 payload shape.
- E: `clustering.spec.ts` — tight-capacity scenario shows AC6 label.

## Out of scope
Changing capacity numbers; re-optimising order (existing optimize step).


## Implementation status (2026-11-17)

Backend only: reachable through the API (`assignments[].window_minutes`) until B1 adds a window input to the wizard. After the verification report: allocation packs to the window (overrun only as flagged overflow), mixed window/lock payloads are rejected, unused bikers get no empty route, and A6 search is branch-and-bound (`split_exact`).
