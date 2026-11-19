# C2 — Show company in list, map (colour), biker view

**Email §3** · **P1** · **Depends on:** C1 · **Size:** M

## Goal
The biker must know which app/bag to take each parcel from (they call the customer and scan the barcode there). Show the company **without needing to click**: distinct colour per company on the map/route and the company name in list rows.

## Context
`frontend/src/components/AddressList.tsx`, `DeliveryMap.tsx`, `StopKanbanBoard.tsx`, `StopDetailsModal.tsx`, `PlannerMapView.tsx`, `SharedRouteView.tsx`; CSS in `App.css`.

## Scope
- `utils/companyColor.ts`: stable colour for a company string (palette of ≥8 colour-blind-safe colours; hash of name → index; same name → same colour across sessions/devices).
- Map markers/segment accent use the company colour; legend lists companies in the current route.
- List rows show a coloured chip with the company name inline (no tap needed). Empty company → no chip.
- Applies to planner map, biker view, shared route view, kanban cards.

## Acceptance criteria
- **C2-AC1** Two stops with different companies → different marker colours; same company → same colour (unit test the colour fn: deterministic, distinct for the 2–3 realistic names).
- **C2-AC2** Each list row shows the company chip visibly without interaction (E2E: chip text present in the row).
- **C2-AC3** Legend shows exactly the distinct companies present, hidden if ≤1 company.
- **C2-AC4** Stops with empty `source_company` render exactly like today (no chip, default colour).
- **C2-AC5** Colour is not the only carrier of info (chip has text) — accessibility.
- **C2-AC6** Works in biker mobile view and public shared view.

## Test plan
- U (frontend, if no unit runner: pure fn exercised via Playwright `page.evaluate` or add Vitest — prefer not adding deps): colour function determinism — AC1.
- E: new `frontend/e2e/company-display.spec.ts` — upload `fama.csv` + `imile.csv` (from C1 fixtures); assert chips (AC2), legend (AC3), shared page (AC6); old fixture without company (AC4).
- M: eyeball colours in light + dark theme (`settings-theme.spec.ts` covers theme toggle).
