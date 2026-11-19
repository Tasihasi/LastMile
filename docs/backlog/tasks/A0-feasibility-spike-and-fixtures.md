# A0 — Feasibility spike + synthetic fixtures

**Email §1** · **Priority P0** · **Depends on:** — · **Size:** S (≈1 day)

Gergő is unsure the zone-first model "can be programmed". Prove or disprove it cheaply, and create
the shared test data every other A-task uses.

## Context
- Current splitting: `backend/planner/clustering.py` (`cluster_stops_weighted`, KMeans on lat/lng — splits zips arbitrarily) and `backend/planner/views/clustering.py` (`_build_assignment_clusters`, `cluster_session`).
- District/zip helpers: `backend/planner/districts.py` (`extract_zip`, `extract_district`).

## Deliverables
1. `backend/planner/testing/zip_fixtures.py` — deterministic generator `make_stops(zip_counts: dict[str,int], seed=42)` returning unsaved `DeliveryStop`-like objects (lat/lng jittered around a per-zip centroid, `postal_code` set). Plus `make_session(...)` that persists them for API tests.
2. A named dataset `REALISTIC_DAY`: ~150–250 stops spread over the 34 zips with uneven density (some zips 1 stop, some 25), and 3–5 bikers.
3. `docs/backlog/A0-spike-report.md` (≤1 page): is zone-first + zip-atomic allocation feasible? Greedy vs. bin-packing sketch, expected worst-case behaviour (one zip bigger than any biker's capacity), recommended algorithm for A2/A5/A6.

## Acceptance criteria
- **A0-AC1** Generator is deterministic: same seed → identical output (ids, coords).
- **A0-AC2** `REALISTIC_DAY` contains ≥1 zip with more stops than a single default route capacity (48) — used later to test forced zip split.
- **A0-AC3** Every generated stop has `postal_code` matching `^1\d{3}$` and lat/lng inside Budapest bbox (47.35–47.60, 18.95–19.20).
- **A0-AC4** Spike report states a go/no-go and names the fallback (e.g., "zip-atomic only + manual override") if no-go.

## Test plan
- U: `backend/planner/test_zip_fixtures.py` — AC1–AC3.
- Review: spike report read by Gergő/Dani (ACs 4).

## Out of scope
Any change to production code paths.
