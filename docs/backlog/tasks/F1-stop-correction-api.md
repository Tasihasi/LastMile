# F1 — Stop correction API (text + coordinates)

**Email §6** · **P0** · **Depends on:** — · **Size:** M

## Goal
Whenever a stop is geocoded wrongly (e.g. Golgota utca 4 → Pilisvörösvár), the planner can fix the **address text** and/or set **exact coordinates**, and everything downstream (clusters, optimization) is consistently invalidated/recomputed.

## Context
- Exists: `update_stop_address` (`PATCH /api/sessions/<id>/stops/<stop_id>/address/`) and `bulk_update_stops`; `geocode_stops` streams geocoding; `remove_stop`.
- Missing: setting lat/lng directly; cascade from child sessions up to the parent; invalidation of optimization.

## Scope
- Extend the address PATCH: accepts `raw_address?`, `postal_code?`, `lat?`, `lng?`.
  - Text changed and no coordinates sent → re-geocode that stop (mock-friendly), set `geocode_status`.
  - Coordinates sent → stored as-is, `geocode_status = "manual"` (new choice; migration), `geocode_error=""`.
- Validate lat 47.0–48.0 / lng 18.5–19.7 loosely (Budapest region) with override flag `force=true` for outside values; otherwise 400 so typos can't throw a pin to the ocean.
- Editing stops on a route that is already optimized sets the route back to "needs optimization" (clear `sequence_order`, geometry, duration). If the stop lives in a sub-route, the parent is not auto-re-split (planner decides) but a `needs_reoptimize` flag is returned.
- Disallowed when route `in_progress`/`finished`.

## Acceptance criteria
- **F1-AC1** Sending `lat/lng` only → stored, `geocode_status == "manual"`, no geocoder call (assert mock not called).
- **F1-AC2** Sending new `raw_address` only → geocoder invoked once, coords updated, status success/failed accordingly.
- **F1-AC3** Coordinates outside the region bbox → 400, unchanged DB; with `force=true` accepted.
- **F1-AC4** `lat` without `lng` (or vice versa) → 400.
- **F1-AC5** On an optimized route, after edit: `sequence_order` cleared for that route, `route_geometry`/`total_duration` null, response `needs_reoptimize: true`.
- **F1-AC6** Route `in_progress`/`finished` → 400; biker → 403.
- **F1-AC7** Editing `postal_code` updates zip-integrity inputs (A3 conflicts recomputed on next fetch).
- **F1-AC8** `bulk_update_stops` accepts the same fields per item (or documents why not).

## Test plan
- A: `StopCorrectionAPITest` — AC1–AC8 using `E2E_MOCK`; patch `geocoder.geocode_address` with `unittest.mock` for call-count assertions.
- Migration: `makemigrations --check`.
- Docs: update `docs/api-reference.md`.

## Out of scope
UI (F2/F3).
