# H3 — Sub-route can be re-split, original split becomes unreachable

**Bug** · **P1** · **Status: fixed in UI (AC1); AC3/AC4 open** · **Depends on:** — · **Related:** H1, H2, F3 · **Size:** S–M

## Problem
After splitting a route (wizard step 5 → split overview), the planner can leave the overview, open an **individual sub-route** and use "Route planner" → step 4 → step 5 → Split. The sub-route is then split again into even fewer routes, the overview switches to the sub-route (`<name>_2`, 1 route) and **the original split overview cannot be reopened**.

## Repro (verified with Playwright, mock backend, planner login)
1. Upload `large_geocoded_60.csv`, uncheck all bikers, "Split automatically" → overview "Large Geocoded 60", 2 routes (`_1`, `_2`, 30 stops each).
2. Dashboard → click the split card → overview reopens (this part works).
3. Click the eye icon ("View full route") on a sub-route → map of the sub-route.
4. Click "Route planner" (shown on the sub-route map) → step 4 → stepper to step 5 → Split dialog for the sub-route.
5. Split → overview is now "Large Geocoded 60_2" with 1 route (`_2_1`); the 2-route overview of the original is gone. Dashboard may show a leftover card "Large Geocoded 60 / Split / 0 stops in 0 sub-routes" (seen once, not traced).

Throw-away repro spec (delete or convert): `frontend/e2e/zz-resplit-repro.spec.ts`.

## Cause (suspected)
- `App.tsx` `handleSelectSession` skips planning steps for sub-routes (`parent_id`), but the "Route planner" button (`openPlanner`) is still rendered for any `not_started` session with stops — so sub-routes can reach step 5.
- `SplitPlannerModal` `onSplit` sets `splitReviewId` to the sub-route, so the app forgets the original parent.
- Backend cluster endpoint accepts a session that already has a `parent_id` — by design (nested splits are tested), so the fix is UI-side.

## Acceptance criteria
- **H3-AC1** A session with a parent has no "Route planner" button and cannot reach wizard step 4/5 (UI).
- **H3-AC2** ~~Backend rejects clustering a session with a `parent_id`.~~ **Not done, deliberately:** the backend explicitly supports nested splits (comment in `views/clustering.py`, test at `tests.py:1505`), so only the UI path is closed. Revisit if nested splits should be forbidden outright.
- **H3-AC3** To re-split, the planner uses "Undo Split" on the parent, or re-splits the parent from its overview; the parent's overview stays reachable from the dashboard after any action on a sub-route.
- **H3-AC4** No empty/orphan split card (0 stops in 0 sub-routes) is left on the dashboard.

## Test plan
- E: `clustering.spec.ts` › "h3: a sub-route has no way back into the planner…" covers AC1 (fails without the fix). AC3/AC4 still need a spec.
- Coordinate with H1 (back to overview from a sub-route) — same screens.
