# C3 — Configurable header → field mapping

**Email §3 (secondary, "ráér")** · **P2** · **Depends on:** C1 · **Size:** M

## Goal
Spreadsheets from each company always have the same headers (Fáma: "Cím"; iMile: "Address"). Let the operator map `"Address"` / `"Cím"` → internal field once, remembered per company. Also needed for the Excel export's column mapping (E1).

## Context
Hard-coded `HEADER_ALIASES` in `backend/planner/parsers.py` (lines ~13–44).

## Scope
- Model `HeaderMapping(company, source_header, field)` (unique on company+normalised header).
- Parsers consult DB mappings for the file's `source_company` first, then built-in aliases.
- Planner endpoints: `GET/PUT /api/header-mappings/` (planner-only). Minimal UI in Settings: table company | header | field(select of known fields).

## Acceptance criteria
- **C3-AC1** With mapping `imile / "Address" → address`, an imile.csv whose only address column is "Address" parses addresses; without mapping it follows previous behaviour.
- **C3-AC2** Mappings are per company: same header under another company is unaffected.
- **C3-AC3** Header matching is case/accent/whitespace-insensitive (reuse `_normalize_header`).
- **C3-AC4** DB mapping overrides built-in alias on conflict.
- **C3-AC5** Invalid target field → 400; biker → 403.
- **C3-AC6** Round trip: PUT then GET returns the same table; survives restart.

## Test plan
- U: parser tests in `ParserCSVTest` style — AC1–AC4.
- A: AC5, AC6.
- E: Settings UI adds a mapping, upload file, parsing succeeds.
