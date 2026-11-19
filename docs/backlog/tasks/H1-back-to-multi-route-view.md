# H1 — Back from single route to multi-route view

**Email §7 (bug)** · **P1** · **Depends on:** — · **Size:** S

## Problem
After opening one sub-route from the multi-route (all-routes) overview there is no way back to the overview except reloading/navigating away. Gergő's earlier letter described this; the latest commit (`0760e1a`, "Open routes in the wizard, add rename and back buttons") added some back buttons — **first reproduce** on current `main` to see what's still broken, and document the repro in the PR.

## Context
`frontend/src/components/PlannerDashboard.tsx`, `ClusterReviewView.tsx`, `PlannerMapView.tsx`, `App.tsx`, `FinishedRouteDetail.tsx`.

## Acceptance criteria
- **H1-AC1** From a single sub-route view (any wizard step) a visible "← All routes" control returns to the parent's multi-route view.
- **H1-AC2** Browser back button does the same (no leaving the app / no blank state).
- **H1-AC3** Returning preserves overview state (scroll, selected filters, unsaved nothing lost) and shows fresh data (e.g. a stop moved inside the sub-route is reflected).
- **H1-AC4** Control is absent when the route has no parent (standalone route).
- **H1-AC5** Works for planner; for biker role the sibling routes are not exposed (biker sees only their route).

## Test plan
- E: add to `clustering.spec.ts` / new `route-navigation.spec.ts` — split → open sub-route → click back (AC1) → `page.goBack()` variant (AC2) → verify data refresh by moving a stop (AC3); standalone route (AC4); biker login (AC5).
