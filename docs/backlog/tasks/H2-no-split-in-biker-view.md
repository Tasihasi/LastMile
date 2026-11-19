# H2 — Biker view must not allow splitting

**Email §7 (bug)** · **P1** · **Depends on:** — · **Size:** S

## Problem
Bikers can see/use the split-route action; only planners may split.

## Context
Backend: `cluster_session` uses `require_planner` — **verify** that the API already rejects bikers (expect 403); the bug is likely UI only, but check both. Frontend: `SplitPlannerModal.tsx`, `PlannerDashboard.tsx`, `AddressList.tsx`, `App.tsx` (role from `useAuth`).

## Acceptance criteria
- **H2-AC1** As biker, no split/cluster control is rendered anywhere (route view, map view, shared view).
- **H2-AC2** `POST /api/sessions/<id>/cluster/` as biker → 403 (and `uncluster`, `move-stop`, `move-zip` likewise).
- **H2-AC3** As planner, split controls remain exactly as before.
- **H2-AC4** Directly URL/state-navigating a biker into the split modal is impossible (no residual modal state).

## Test plan
- A: `RoleEnforcementTest` — AC2 for each planner-only endpoint listed.
- E: `biker-journey.spec.ts` — assert `getByRole('button', {name: /split|osztás/i})` count 0 (AC1, AC4); `planner-journey.spec.ts` unchanged (AC3).
