# LastMile backlog — from Gergő's email (2026-11-17)

> **Must conditions (whole app):** 15-minute day, addresses placed where they really are, routes truly optimized (not lines between points). See `CLAUDE.md` and `backend/planner/test_must_conditions.py`.

Source: Gergő's follow-up email after the walkthrough (Hungarian). Each numbered point of the
email is split into small, independently shippable tasks. **One task = one file = one PR.**
A fresh Claude session should be able to open exactly one task file plus this README and do the work.

## How to use (for a Claude session picking up a task)

1. Read this README (conventions, commands, DoD) and your task file. Nothing else is required.
2. Check `Depends on` in the task file. If a dependency is not merged to `main`, stop and say so.
3. Branch: `feature/<task-id>-<slug>` (e.g. `feature/a2-zip-atomic-distribution`), PR into `main`.
4. Write the tests listed in **Test plan** *first* (or alongside). Every Acceptance Criterion (AC) must map to at least one test or one manual-script step. Name tests with the AC id, e.g. `test_a2_ac1_no_zip_spans_two_routes`.
5. Update `CHANGELOG.md` and, if user-facing, `frontend/src/content/user-guide-*.md` / `docs/api-reference.md`.
6. Do not widen scope. If you find something adjacent, note it in the PR description, don't fix it.

## Test layers and commands

| Tag | Layer | Where | Run |
|-----|-------|-------|-----|
| U | Backend unit | `backend/planner/tests.py` (or new `backend/planner/test_<topic>.py`) | `cd backend && python manage.py test planner.test_<topic>` |
| A | Backend API | `backend/planner/test_e2e_api.py` (uses `_auth_client(username, role)`) | `cd backend && python manage.py test planner.test_e2e_api` |
| E | Browser E2E (Playwright) | `frontend/e2e/*.spec.ts`, fixtures in `frontend/e2e/fixtures.ts`, data in `frontend/e2e/test-data/` | `cd frontend && npm run test:e2e -- <spec>` (starts backend with `E2E_MOCK=true`, mock geocoder/optimizer) |
| M | Manual script | numbered steps in the task file | run in `npm run dev` + `python manage.py runserver` |

Always green before PR (mirrors `.github/workflows/ci.yml`):

```
cd backend  && ruff check . && ruff format --check . && python manage.py test
cd frontend && npm run lint && npx tsc -b && npm run build
cd frontend && npm run test:e2e        # when UI touched
```

Mocking notes: `settings.E2E_MOCK` makes `geocoder._mock_geocode` and `optimizer._mock_optimize` deterministic.
Never call Nominatim/ORS from automated tests.

## Definition of Done (every task)

- All ACs in the task file demonstrably pass (tests named by AC id).
- CI commands above are green; no unrelated diffs.
- New behaviour has at least one negative/edge test (empty input, unauthorized role, etc.).
- Planner-only endpoints use `require_planner`; bikers get 403 (test it).
- CHANGELOG entry + docs touched where noted.

## Priorities (my assumption from the email — Gergő said "can't start using it without" = P0)

- **P0** go-live blockers: A0–A4, B1, C1, E1, F1–F3
- **P1** speeds up / sharpens: A5, A6, B2, C2, D1, G1, G2, H1, H2, E2
- **P2** explicitly "later": B3, B4, C3, I1

Dani's commitment: **point 1 (Epic A) by end of next week (≈ Fri 2026-11-27)**, then sync with Gergő.
Barna: sort-app (E2 contract), geocoding evaluation (G2). The A-chain is the critical path.

## Index

| ID | Title | Email § | Pri | Depends on |
|----|-------|---------|-----|-----------|
| [A0](tasks/A0-feasibility-spike-and-fixtures.md) | Feasibility spike + synthetic fixtures | 1 | P0 | — |
| [A1](tasks/A1-zone-config.md) | Zone config (34 zips → 16 zones) | 1 | P0 | — |
| [A2](tasks/A2-zip-atomic-distribution.md) | Zip-atomic distribution (the minimum criterion) | 1 | P0 | A1 |
| [A3](tasks/A3-zip-integrity-validator.md) | Zip-integrity validator + warnings in API/UI | 1 | P0 | A1 |
| [A4](tasks/A4-move-zip-override.md) | Move a whole zip to another biker (override) | 1 | P0 | A2, A3 |
| [A5](tasks/A5-zone-first-capacity-allocation.md) | Zone-first, time-capacity-aware allocation | 1 | P1 | A2, B1, B2 |
| [A6](tasks/A6-minimal-zone-splitting-fallback.md) | Minimal zone-splitting fallback | 1 | P1 | A5 |
| [B1](tasks/B1-time-config-and-depot-times.md) | Time config + depot start/return times | 2 | P0 | — |
| [B2](tasks/B2-route-duration-estimate-overrun.md) | Route duration estimate + 7.5 % overrun status | 2 | P1 | B1 |
| [B3](tasks/B3-biker-speed-multiplier.md) | Per-biker service-time multiplier | 2 | P2 | B1 |
| [B4](tasks/B4-per-route-service-time.md) | Per-route service-time override | 2 | P2 | B1 |
| [C1](tasks/C1-source-company-column.md) | `source_company` from uploaded filename | 3 | P0 | — |
| [C2](tasks/C2-company-in-ui.md) | Show company in list, map (colour), biker view | 3 | P1 | C1 |
| [C3](tasks/C3-header-mapping-config.md) | Configurable header → field mapping | 3 | P2 | C1 |
| [D1](tasks/D1-mobile-split-list-map.md) | Biker mobile: list + map side by side | 4 | P1 | — |
| [E1](tasks/E1-excel-export.md) | Excel export per day | 5 | P0 | C1 |
| [E2](tasks/E2-sort-app-contract.md) | Sort-app export contract + dummy Excel | + | P1 | E1 (format) |
| [F1](tasks/F1-stop-correction-api.md) | Stop correction API (text + coordinates) | 6 | P0 | — |
| [F2](tasks/F2-draggable-marker.md) | Drag-and-drop pin on map | 6 | P0 | F1 |
| [F3](tasks/F3-edit-addresses-from-any-step.md) | Go back and edit addresses from any wizard step | 6 | P0 | F1 |
| [G1](tasks/G1-geocoder-provider-abstraction.md) | Geocoder provider abstraction | 6 | P1 | — |
| [G2](tasks/G2-geocoding-accuracy-evaluation.md) | 97 % geocoding accuracy evaluation (Barna) | 6 | P1 | G1 |
| [H1](tasks/H1-back-to-multi-route-view.md) | Back from single route to multi-route view | 7 | P1 | — |
| [H2](tasks/H2-no-split-in-biker-view.md) | Biker view must not allow splitting | 7 | P1 | — |
| [I1](tasks/I1-admin-api-settings.md) | Admin page for external-service API keys | + | P2 | G1 |

Epic **J** (address pipeline: parallel batches of 5, rule-based Hungarian parser, Google last resort, review queue) is planned in a single file, [address-pipeline.md](address-pipeline.md) (tasks J0–J8, depends on G1; implemented, see its status line and [self-hosted-nominatim.md](../self-hosted-nominatim.md)).

Suggested order: `A0 ∥ A1 ∥ B1 ∥ C1 ∥ F1 ∥ H2` → `A2, A3, F2, F3, E1` → `A4` → `A5, B2, C2` → `A6` → rest.

## Open questions (blockers to raise with Gergő — do not guess)

1. **The zone spreadsheet** (34 zips, 16 zones, from row 22) was only linked, not attached. A1 needs it. Until then A1 ships a clearly-marked placeholder.
2. Depot address is **Orczy út 45** (Budapest VIII) — confirm lat/lng or let geocoder resolve it; used as route start/end everywhere.
3. 48-hour delivery deadline: is "which zips did we attempt today" tracking in scope? (Email implies zip-integrity is the *proxy*; no tracking feature requested. Assumed out of scope.)
4. Overrun rule (B2): "max 7.5 % over the time of one route" — assumed relative to the available window (return − start).
5. Sort-app: separate repo/app (agreed with Dani + Barna); only the Excel contract (E2) lives here.
