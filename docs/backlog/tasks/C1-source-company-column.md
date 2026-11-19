# C1 — `source_company` from uploaded filename

**Email §3** · **P0** · **Depends on:** — · **Size:** S–M

## Goal
Every imported row records which company/file it came from. Operators rename the 2–3 files before import (e.g. `csomagkézbesítés lista 2611131236.xlsx` → `fáma.xlsx`, `parcels 11132026.csv` → `imile.csv`); the system copies the **file name (without extension)** into a new column on each stop.

## Context
- Upload: `upload_file` in `backend/planner/views/sessions.py` (already accepts multiple files and builds route name from file names via `_route_name_from_files`); parsers in `backend/planner/parsers.py`; model `DeliveryStop`; `_normalize_row`.
- Child sessions copy stops field-by-field in `cluster_session` / move-stop — **new field must be copied there too** (easy to forget).

## Scope
- `DeliveryStop.source_company` (`CharField(max_length=100, blank, default="")`), migration `0012+`.
- `upload_file`: after parsing each file, set `source_company = normalized(stem(filename))` on its rows. Normalisation: strip, collapse whitespace, keep Unicode (fáma stays fáma), max 100 chars.
- Preserve through: cluster split, uncluster, move-stop, bulk update, shared route payload, serializers (`DeliveryStopSerializer`).
- Optional multipart field `company_names[]` overriding stems (not required now; skip if cheap not available).

## Acceptance criteria
- **C1-AC1** Upload `fáma.xlsx` + `imile.csv` in one request → stops from the first all have `source_company == "fáma"`, second `"imile"`.
- **C1-AC2** `csomagkézbesítés lista 2611131236.xlsx` → `"csomagkézbesítés lista 2611131236"` (no magic parsing; operator renames).
- **C1-AC3** Extension stripped case-insensitively (`IMILE.CSV` → `IMILE`); name with dots (`a.b.csv` → `a.b`).
- **C1-AC4** Single upload still works; field present on every stop.
- **C1-AC5** Field survives: split into sub-routes, uncluster, move-stop, `GET /api/shared/<id>/` — assert in each.
- **C1-AC6** Existing stops (pre-migration) get `""`, API returns `""` not null.
- **C1-AC7** Filename containing path separators/control characters is sanitised (no `..`, `/`).

## Test plan
- U: normaliser function `company_from_filename` — AC2, AC3, AC7 table-driven.
- A: `UploadAPITest` — AC1, AC4, AC6; `SplitPlannerAPITest` / `SharingTest` — AC5.
- Migration: `makemigrations --check`.
- Fixtures: create two tiny CSVs in `frontend/e2e/test-data/` named `fama.csv`, `imile.csv`.

## Out of scope
Showing it in the UI (C2), Excel column (E1), header mapping (C3).
