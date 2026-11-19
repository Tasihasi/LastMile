# E2 — Sort-app contract + dummy Excel

**Email "+ sorting app"** · **P1** · **Depends on:** E1 (column definition) · **Size:** S · **Owner:** Barna (with Dani)

## Goal
The sorting-assist app is a **separate app** that consumes LastMile's export. Freeze the interface now so both sides develop in parallel: a written contract + a hand-made dummy Excel that the sort-app can test against *before* the real export exists.

## Deliverables
1. `docs/contracts/sort-export.md`: sheet name, header names/order (from E1), types per column, encoding, row ordering, invariants (per biker `Sorrend` contiguous 1..N; `Összesen` constant per biker; unique `Csomagazonosító`), version field (`contract_version: 1` in a second hidden sheet `meta` or document property), how breaking changes are announced.
2. `example_files/sort_export_dummy_v1.xlsx` — 3 bikers, ~40 rows, ≥2 companies, a same-address pair, Hungarian accents, one empty `Cég`.
3. A validator script `backend/scripts/validate_sort_export.py <file>` (pure openpyxl) that checks the invariants and exits non-zero with a readable message.

## Acceptance criteria
- **E2-AC1** Validator passes on the dummy file.
- **E2-AC2** Validator fails (distinct message each) when: header missing/renamed, duplicate `Csomagazonosító`, `Sorrend` gap, `Összesen` ≠ count of that biker's rows, `Sorrend/Összesen` text mismatch.
- **E2-AC3** The real E1 export (from the E1 API test) passes the same validator — add as a test so the contract can't drift.
- **E2-AC4** Contract doc lists every column from E1 and states which are required.

## Test plan
- U: `test_sort_export_contract.py` — AC1, AC2 (mutate dummy in memory per case), AC3 (generate via E1 endpoint).
- Review: Barna confirms the contract is sufficient for the sort-app (record in PR).
