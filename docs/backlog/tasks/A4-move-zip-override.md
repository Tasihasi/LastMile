# A4 — Move a whole zip to another biker (override)

**Email §1** · **P0** · **Depends on:** A2, A3 · **Size:** M

## Goal
"If I can override and shuffle a whole irányítószám to another courier, we can use the software." One action moves **every** stop of a zip (optionally a whole zone) from route X to route Y.

## Context
- Existing single-stop move: `move_stop` view + `MoveStopModal.tsx`. Bulk: `bulk_update_stops`.
- Sub-routes are `DeliverySession` children (`parent`); only `not_started` sub-routes can change.

## Scope
- `POST /api/sessions/<parent_id>/move-zip/` body `{zip: "1082", to_session_id: "<uuid>"}` (also accept `zone_id` → moves all zips of the zone; XOR with `zip`).
- Moves all non-excluded stops of that zip from *all other* sub-routes of the parent into the target. Resets `sequence_order` / optimization fields of every touched route (they must be re-optimized) — reuse whatever `move_stop` does.
- UI: in review view, each zip chip/row gets "Move zip…" → modal choosing target route (shows resulting stop counts). Confirm applies; toast on success.

## Acceptance criteria
- **A4-AC1** After move, all stops of zip Z are in the target route and in no other; `zip_conflicts` (A3) no longer lists Z.
- **A4-AC2** Stops of other zips are untouched in all routes.
- **A4-AC3** Touched routes lose their optimized order/geometry/duration (status back to "needs optimization"); untouched routes keep theirs.
- **A4-AC4** `zone_id` variant moves every zip of that zone present in the parent.
- **A4-AC5** Sending both `zip` and `zone_id`, or neither → 400. Unknown zip with no stops → 400 with clear message. Target not a child of that parent → 400/404.
- **A4-AC6** Target or any source route `in_progress`/`finished` → 400 (consistent with existing move-stop rules).
- **A4-AC7** Biker role → 403; planner who does not own the parent → 403/404 like other endpoints.
- **A4-AC8** Atomic: any failure leaves DB unchanged (wrap in `transaction.atomic`; test with injected failure).
- **A4-AC9** UI shows resulting counts before confirm and updates the review view without page reload.

## Test plan
- A: `test_e2e_api.py::MoveZipAPITest` — AC1–AC8 (set up with A0 `make_session`, 3 routes, zip split across 2).
- E: new `frontend/e2e/move-zip.spec.ts` — upload `postal_codes.csv`, split into 3, open "Move zip…" for a zip, pick target, assert chip moves, banner (A3) disappears, counts update (AC9).
- Regression: existing move-stop tests.

## Out of scope
Drag-and-drop of zip chips (nice follow-up), auto balancing.
