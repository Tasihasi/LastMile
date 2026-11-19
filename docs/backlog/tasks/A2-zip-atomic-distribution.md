# A2 — Zip-atomic distribution (the minimum criterion)

**Email §1** · **P0** · **Depends on:** A1 (A0 fixtures) · **Size:** M

## Goal
Gergő's hard requirement: **all stops with the same irányítószám go to exactly one route.** Never two.
Even if the algorithm combines zips badly, this alone makes the tool usable (planner fixes combos via A4).

## Context
- `cluster_session` in `backend/planner/views/clustering.py` calls `cluster_stops` (auto) or `_build_assignment_clusters` (with `assignments`, zip/district locks). Both can split a zip across clusters because KMeans runs on stop coordinates.
- Invalid cases: stops with empty/unknown `postal_code` (can't be grouped).

## Scope
- New pure function in `backend/planner/clustering.py`: `cluster_zip_atomic(stops, n_routes | targets, depot, max_stops)`:
  1. Group stops by zip (a "zip group" is indivisible).
  2. Cluster the *groups* (centroid per group, weighted by stop count) geographically (KMeans on centroids or greedy nearest-fit), balancing stop counts toward targets.
  3. Return clusters of stops.
- `cluster_session` uses it by default. Old stop-level KMeans stays only as an explicit opt-out? **No — remove from the default path.**
- Stops without a zip: group them by themselves into a single `"unknown"` bucket, assigned to the smallest route, and returned in response field `unzipped_stop_ids` (visible warning, A3).
- If one zip group exceeds `max_stops`: keep it whole (it will be one oversized route) and flag it in `oversized_zips` — splitting is A6's job, not A2's.

## Acceptance criteria
- **A2-AC1** For any input, no zip (non-empty) appears in more than one resulting cluster. (Property test over ≥50 random seeds from A0 generator.)
- **A2-AC2** Every input stop appears in exactly one cluster (no loss, no duplicates).
- **A2-AC3** With `n_routes=k` returns at most k non-empty clusters and never an empty cluster when groups ≥ k.
- **A2-AC4** Balance: on `REALISTIC_DAY`, max route size ≤ 1.5 × average **unless** a single zip forces it (assert the exception explicitly).
- **A2-AC5** Zip group larger than `max_stops` is kept whole and listed in `oversized_zips`.
- **A2-AC6** Stops with no zip are bucketed together, listed in `unzipped_stop_ids`, request still 200.
- **A2-AC7** Deterministic: same input → same output.
- **A2-AC8** Existing `assignments` path with `zip`/`district` locks still works and also never splits a zip (locked zip + unlocked remainder of same zip → remainder follows the lock).

## Test plan
- U: `test_clustering_zip_atomic.py` — AC1 (property loop), AC2, AC3, AC4, AC5, AC7 on pure function.
- A: `SplitPlannerAPITest` additions — AC6, AC8 via `POST /api/sessions/<id>/cluster/`; assert response contains `oversized_zips`, `unzipped_stop_ids`.
- E: extend `frontend/e2e/clustering.spec.ts` — upload `needs_geocoding_60.csv`/`postal_codes.csv`, split into 3, assert in the review UI that no zip label appears under two route cards.
- Regression: all existing `SplitPlannerAPITest`/`SplitCountsTest` must still pass (adjust only where they encoded the old splitting behaviour; call it out in the PR).

## Out of scope
Time capacity (A5), zone-level preference (A5), splitting oversized zips (A6), UI to move zips (A4).
