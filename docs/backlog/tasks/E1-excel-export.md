# E1 — Excel export per day

**Email §5** · **P0** · **Depends on:** C1 · **Size:** M

## Goal
At the end of the process, export one `.xlsx` containing **every package of the day**, used for physically sorting parcels in route order. The packer must also know the **total count per route** (so they know when they're done): rendered as `16/45`.

## Columns (exact order, Hungarian headers)
| # | Header | Content |
|---|--------|---------|
| a | `Csomagazonosító` | `product_code` |
| b | `Cím` | `irányítószám, utca házszám` (composed from stop: zip + street + number; fall back to `raw_address`) |
| c | `Cég` | `source_company` |
| d | `Futár` | biker username / display name of the route owner |
| e | `Sorrend` | numeric position in route (`sequence_order`, 1-based) |
| f | `Összesen` | total stops in that route |
| g | `Sorrend/Összesen` | text `"16/45"` |

Two numeric columns (e, f) **and** the combined text (g) so the sorter can sort numerically *and* read at a glance. Sort order of the sheet: Futár, then Sorrend. (Open design point for Barna: font weight/size of the number in g — can be styled bold-first-number in rich text; don't block on it.)

## Context
- Export endpoint is new: `GET /api/sessions/<parent_id>/export.xlsx` (parent with optimized sub-routes) and/or `GET /api/export/?date=YYYY-MM-DD`. Use `openpyxl` (already a dependency via `parse_xlsx`; verify in `requirements.txt`).
- Excluded stops (`excluded=True`) are not exported. Unoptimized routes → 409 with message (no order to export).

## Acceptance criteria
- **E1-AC1** Workbook has one sheet, header row exactly as above, then one row per non-excluded stop of all sub-routes of the parent.
- **E1-AC2** Row count equals number of non-excluded stops; no duplicates; no missing.
- **E1-AC3** For each biker, `Sorrend` runs 1..N contiguous with `Összesen == N`, and `Sorrend/Összesen` text equals `f"{e}/{f}"`.
- **E1-AC4** `Cím` contains zip first; `Cég` equals `source_company` (empty string if none).
- **E1-AC5** Route not yet optimized → 409 `{error}`; parent without sub-routes (single route) works too (one biker).
- **E1-AC6** Unicode (á é ő ű, "fáma") round-trips intact when read back by openpyxl.
- **E1-AC7** Planner-only: biker 403, anonymous 401; planner who doesn't own the session 404/403.
- **E1-AC8** Response headers: correct xlsx content-type and `Content-Disposition` filename containing the date, e.g. `lastmile_2026-11-17.xlsx`.
- **E1-AC9** UI: "Export Excel" button visible at the final step; triggers download.
- **E1-AC10** Stops with `\n`/`=`-leading text don't create formula injection (prefix `'` or set data type string for cells starting with `= + - @`).

## Test plan
- A: `ExportAPITest` in `test_e2e_api.py` — build session (A0 `make_session`, 2 bikers, optimized via mock) → download → read with `openpyxl.load_workbook(BytesIO(resp.content))`; assert AC1–AC8, AC10.
- E: `planner-journey.spec.ts` extension — wait for download event (`page.waitForEvent('download')`), assert file name and non-zero size (AC9).
- Contract tie-in: the fixture produced here is the input for E2 dummy Excel.

## Out of scope
Header mapping for import (C3), sort-app (E2).
