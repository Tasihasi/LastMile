# G2 — 97 % geocoding accuracy evaluation

**Email §6** · **P1** · **Depends on:** G1 (for pluggable providers) · **Owner:** Barna (+Dani, needs LastMile access) · **Size:** M (research)

## Goal
Pick a geocoding provider reaching **≥ 97 % correctly placed addresses** on real Budapest V–IX delivery data. Gergő can only eyeball correctness today — define a measurable methodology. Budget idea: one RouteXL day pass (~2000 Ft; tests ~5 providers on any number of 100-address routes).

## Deliverables
1. `docs/research/geocoding-evaluation.md`: methodology, sample, results table per provider, recommendation.
2. Evaluation harness `backend/scripts/geocode_eval.py <addresses.csv> --providers a,b,c` outputting CSV/markdown per provider.
3. A **gold set**: ≥ 200 addresses (anonymised: street+number+zip only, no names/phones) with hand-verified lat/lng, stratified across zips/districts (V–IX) and difficult cases (no house number, "u." abbreviations, ground-floor/door suffixes, Hungarian diacritics). Stored under `backend/planner/sample_data/geocode_gold.csv`. **No real personal data in the repo.**

## Definition of "correct" (proposed — confirm with Gergő)
- Distance error ≤ **50 m** to ground truth → correct; 50–200 m → "near"; > 200 m or outside the expected zip polygon/district → wrong. Report % per class, per provider and per district.
- Also report: `no result` rate, outside-Budapest rate (Pilisvörösvár-type catastrophic errors), median/p95 error.

## Acceptance criteria
- **G2-AC1** Gold set ≥ 200 rows, every row has verified coordinates and a `verified_by` + method note; stratification table in the report.
- **G2-AC2** Harness is reproducible: same input+provider → same CSV (cache provider responses in `scratch/`, git-ignored).
- **G2-AC3** Report lists ≥ 3 providers with the metrics above and a clear pick, or states none reaches 97 % and proposes mitigations (e.g., zip-constrained geocoding, confidence threshold → manual review list in F3).
- **G2-AC4** Catastrophic errors (> 5 km off) listed explicitly with their input strings.
- **G2-AC5** Repo contains no API keys and no real customer PII (review check).
- **G2-AC6** Cost estimate for expected volume (packages/day × providers) vs. the 20–80k HUF/month total external-services budget.

## Test plan
- U: `test_geocode_eval.py` — distance function (haversine) known values; classification boundaries at exactly 50/200 m; harness runs with `MockProvider` and produces expected table shape.
- Review: Gergő sanity-checks 10 random verdicts by eye.
