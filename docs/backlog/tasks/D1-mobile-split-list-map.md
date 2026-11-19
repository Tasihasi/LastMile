# D1 — Biker mobile: list + map side by side

**Email §4** · **P1** · **Depends on:** — (C2 chips will appear automatically later) · **Size:** M

## Goal
On a phone, a biker sees list and map **nearly in parallel** (e.g., a bottom sheet / swipe-to-collapse panel). Speeds up morning packing, lets experienced riders skip looking at the map, and lets them spot multiple parcels to the same address (adjacent rows).

## Context
`frontend/src/components/AddressList.tsx`, `DeliveryMap.tsx`, `App.tsx`, `App.css`; mobile test precedent: `claude_exec_plan/ux_test_report_mobile_2026_04_10.md`, `frontend/e2e/biker-journey.spec.ts`.

## Scope
- Mobile viewport (<768 px) biker route view: map fills the screen; list is a draggable bottom sheet with 3 snap states: collapsed (peek ≈ current stop), half, full.
- Tapping a list row focuses its marker; tapping a marker scrolls list to the row and highlights it.
- Desktop layout unchanged.
- Rows with identical `raw_address` are visually grouped (subtle group bracket) — supports "spot same-address parcels".

## Acceptance criteria
- **D1-AC1** At 390×844 both list (peek) and map are visible at once, without navigating.
- **D1-AC2** Sheet has collapsed/half/full states, reachable by drag *and* by a button (accessibility fallback for non-drag).
- **D1-AC3** Selecting a stop in the list pans the map to it and highlights the marker; selecting a marker highlights the list row (scrolled into view).
- **D1-AC4** Marking a stop delivered/failed (existing actions) still works in every sheet state and does not collapse the sheet unexpectedly.
- **D1-AC5** Desktop (≥1024 px) screenshot-level behaviour unchanged (existing e2e passes untouched).
- **D1-AC6** Consecutive stops with the same address are grouped visually.
- **D1-AC7** No horizontal scroll, touch targets ≥ 44 px.

## Test plan
- E: new `frontend/e2e/biker-mobile-split.spec.ts` with `test.use({ viewport: {width:390,height:844}, hasTouch:true })` — AC1–AC4, AC6, AC7 (`scrollWidth <= clientWidth`).
- E: existing `biker-journey.spec.ts`, `map-interactions.spec.ts` unchanged and green — AC5.
- M: real phone check or Chrome device emulation; record GIF for the PR.
