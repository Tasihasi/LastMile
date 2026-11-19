# F3 — Go back and edit addresses from any wizard step

**Email §6** · **P0** · **Depends on:** F1 · **Size:** M

## Goal
"At any point I can go back to the very first step and keep editing the text address and/or move the dot." A bad address ruins both splitting and optimization, so the planner must be able to fix it at any stage without losing work.

## Context
`frontend/src/components/RouteWizard.tsx`, `WizardFooter.tsx`, `utils/wizard.ts` (WizardStep 1–5), `AddressList.tsx`, `StopDetailsModal.tsx`.

## Scope
- From every wizard step the "back"/step indicator can return to the address step (step 1/2) **without discarding** later-step state that is still valid.
- Editing an address text inline → F1 → shows result (re-geocoded pin).
- If edits invalidate later steps (clusters, optimization) show a clear confirmation: "Ez érvényteleníti az optimalizálást; újra kell futtatni" — listing what gets invalidated — and proceed only on confirm.
- After finishing edits the planner returns to the step they left, with invalidated artifacts flagged.
- Failed geocodes are listed on top ("Hibás címek") for fast fixing.

## Acceptance criteria
- **F3-AC1** From steps 2, 3, 4 and 5 there is a way to reach the address step; wizard state (selected bikers, times from B1) is retained.
- **F3-AC2** Editing a stop's text shows the new geocoded position (mock) and persists after reload.
- **F3-AC3** Editing in an already-optimized route triggers the invalidation confirm; cancel leaves everything unchanged; confirm clears optimization (F1-AC5).
- **F3-AC4** Editing in a not-yet-split route triggers no confirm.
- **F3-AC5** Failed-geocode stops appear in a dedicated list; fixing one removes it from the list.
- **F3-AC6** Stops can still be removed (existing) from this view; zip edit (F1-AC7) updates zip chips.

## Test plan
- E: extend `route-wizard.spec.ts` — for each step 2–5 click back to address step, edit, return (AC1–AC4); use `needs_geocoding.csv` for AC5.
- Regression: existing wizard specs green.
- M: confirm no data loss by checking Network tab shows no re-upload.
