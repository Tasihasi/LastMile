# F2 — Drag-and-drop pin on the map

**Email §6** · **P0** · **Depends on:** F1 · **Size:** M

## Goal
Planner drags a stop's dot to the right place on the map; the new coordinates are saved via F1.

## Context
Leaflet in `frontend/src/components/DeliveryMap.tsx` / `PlannerMapView.tsx`. API client `frontend/src/api/client.ts`.

## Scope
- "Edit locations" toggle (default off, so bikers/planners don't drag by accident). When on, markers are draggable (`draggable: true`, `dragend` handler).
- On drop: optimistic move, call F1 with new lat/lng, toast "Pozíció mentve"; on failure revert the marker and show error toast.
- Marker popup/tooltip shows address text and an "Edit address" action (opens F3 editor).
- Not available in biker role or for non-`not_started` routes.

## Acceptance criteria
- **F2-AC1** Toggle off → markers not draggable. Toggle on → draggable.
- **F2-AC2** Dragging a marker sends exactly one PATCH with the dropped lat/lng; after reload the marker is at the new position, `geocode_status == manual`.
- **F2-AC3** API failure (simulate 400) → marker snaps back, error toast, no stale state.
- **F2-AC4** After a move on an optimized route, UI shows "needs re-optimization" and the Optimize action is offered (F1-AC5).
- **F2-AC5** Biker role never sees the toggle.
- **F2-AC6** Works on touch (long-press drag) — manual check at least.

## Test plan
- E: new `frontend/e2e/edit-location.spec.ts` — enable toggle, drag marker via `page.mouse` (down/move/up on marker element), intercept `PATCH …/address/` with `page.waitForRequest` and assert payload (AC2); route-mock a 400 for AC3; login as biker for AC5.
- M: AC6 on device emulation.
