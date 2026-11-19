# A3 — Zip-integrity validator + warnings in API/UI

**Email §1** · **P0** · **Depends on:** A1 · **Size:** S–M

## Goal
Whatever creates or edits routes (auto split, manual move-stop, drag in kanban), the planner must *see* when a zip is spread over >1 route. This is the safety net behind the minimum criterion.

## Context
- Review UI: `frontend/src/components/ClusterReviewView.tsx`, `StopKanbanBoard.tsx`, `MoveStopModal.tsx`; endpoints `move-stop`, `bulk_update_stops`.
- Types: `frontend/src/types/index.ts`.

## Scope
- Pure function `find_zip_conflicts(sub_routes) -> [{zip, zone, routes:[{session_id,name,count}]}]` in `backend/planner/zones.py` or `clustering.py`.
- `GET /api/sessions/<parent_id>/` (parent with sub-routes) and the cluster / move-stop responses include `zip_conflicts`.
- UI: banner in review view "N irányítószám több körben szerepel: 1082 (Route_1: 4, Route_2: 2)" + per-route chip highlighting split zips. No banner when clean.

## Acceptance criteria
- **A3-AC1** Zero conflicts → `zip_conflicts == []`; no banner.
- **A3-AC2** Zip 1082 on two routes → exactly one conflict entry listing both routes with counts.
- **A3-AC3** Excluded/removed stops (`excluded=True`) are ignored.
- **A3-AC4** Stops without a zip never produce a conflict.
- **A3-AC5** After `move-stop` that creates a split, the response contains the conflict; after a move that resolves it, the list is empty.
- **A3-AC6** Banner is visible in the review view when conflicts exist and names zip + routes; clicking it highlights/filters the affected stops (nice-to-have: scroll to first).
- **A3-AC7** Conflict warning is informational — it never blocks saving/optimizing (planner may knowingly split, A6).

## Test plan
- U: `find_zip_conflicts` — AC1–AC4.
- A: AC5 via `POST move-stop` before/after; check serialized `zip_conflicts`.
- E: `clustering.spec.ts` — build a conflict by moving one stop (existing move-stop modal), assert banner text; move it back, assert banner gone (AC6).
- M: confirm AC7 — click "Optimize" with a conflict active; it proceeds.

## Out of scope
Auto-fixing conflicts (A4 manual, A6 auto).
