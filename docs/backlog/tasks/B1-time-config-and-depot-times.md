# B1 — Time config + depot start/return times

**Email §2** · **P0** · **Depends on:** — · **Size:** M

## Goal
In the "Bikers" wizard step, planner enters per biker **depot departure time** (team deadline: route packed and ready) and **depot return time** (biker's deadline). Their difference is the available time. Service time per address, average travel time and break are **global constants set in code** (no UI yet).

## Context
- Wizard: `frontend/src/components/RouteWizard.tsx`, `BikerPicker.tsx`, `SplitPlannerModal.tsx`, `frontend/src/utils/wizard.ts`.
- Backend: `_parse_assignments` in `backend/planner/views/clustering.py` (assignments payload); `DeliverySession` model.

## Scope
- `backend/planner/timing.py` with a single config block:
  `SERVICE_TIME_PER_STOP_MIN = 2.0`, `AVG_TRAVEL_MIN_PER_STOP = …`, `BREAK_MIN = …`, `OVERRUN_TOLERANCE = 0.075`. One place to edit.
- Model: add `depot_start` / `depot_return` (`TimeField`, null) to `DeliverySession` (migration `0012`). Date is implicit (the day of planning).
- Assignment payload gets `depot_start`, `depot_return` (`"HH:MM"`), validated and persisted on the child session; serializers expose them + computed `available_minutes`.
- UI: two time inputs per biker row in the Bikers step; live "Available: 4 h 30 min".

## Acceptance criteria
- **B1-AC1** Valid `"07:30"`/`"12:00"` → persisted; `available_minutes == 270` in session JSON.
- **B1-AC2** `depot_return <= depot_start` → 400 with clear message; malformed time → 400.
- **B1-AC3** Omitted times → still works (nullable; behaves like today) — backwards compatible.
- **B1-AC4** Changing `SERVICE_TIME_PER_STOP_MIN` in `timing.py` is the only edit needed to change the value everywhere (grep-check: no other literal `2` minutes in backend/frontend logic).
- **B1-AC5** UI shows computed available time and blocks "Next" when return ≤ start (inline error).
- **B1-AC6** Values survive page reload and re-opening the route in the wizard.

## Test plan
- U: `test_timing.py` — AC1, AC2 helper `available_minutes(start, return)`, AC4 constants exist.
- A: `SplitPlannerAPITest` — AC1, AC2, AC3 through `/cluster/`.
- E: `route-wizard.spec.ts` — fill times, see computed duration (AC5), reload and reopen (AC6).
- Migration: `python manage.py makemigrations --check` clean.

## Out of scope
Using the numbers for allocation (A5) or warnings (B2); per-biker multiplier (B3).
