# Epic J — Address pipeline: parallel geocoding + rule-based Hungarian address parser (plan, 2026-11-19)

> **Must conditions (whole app):** 15-minute day, addresses placed where they really are, routes truly optimized. See `CLAUDE.md`.
> This epic serves #1 (a 600-700 address upload must not leave dozens of addresses to fix by hand, and the geocode step
> must be fast) and #2 (every accepted coordinate must agree with the address's postal code / settlement).

Status: **implemented in one PR (J0-J8; D1-D4 still need a decision, see section 8).** Related: [G1](tasks/G1-geocoder-provider-abstraction.md) (provider abstraction),
[G2](tasks/G2-geocoding-accuracy-evaluation.md) (accuracy evaluation), [real-services-smoke.md](real-services-smoke.md).

## 1. Problem

- `_geocode_stream` (`backend/planner/views/sessions.py`) geocodes **one address at a time** and `geocoder._rate_limit()`
  caps it at 1 request/s. 700 addresses = ~12 min for this step alone, most of the 15-minute budget.
- Nominatim's first hit is taken as-is; a failure goes **straight to the user** to type a fix. Only parsing today is the
  regex `districts.extract_postal_code`. `parsers.py` maps file columns, it does not understand free text.
- At a few percent failure rate, 700 addresses = tens of manual fixes. Goal: shrink that number as far as deterministic
  rules can, and make the leftovers one-click.

## 2. Constraints and decisions

| Constraint | Consequence |
|------------|-------------|
| **No AI** (user requirement) | Parser is rules + lookup tables + edit-distance only. libpostal is excluded (trained model). |
| Public Nominatim forbids parallel/heavy use (1 req/s) | Real parallelism needs a **self-hosted Nominatim (Hungary extract)**. Base URL + concurrency are settings; if the URL is the public one a shared limiter clamps to 1 req/s. |
| Must #2: addresses are where they really are | Accept a result only if it agrees with the parsed zip/settlement. Never scatter or guess. |
| Strict pinning (house-number match, 2 m) was tried and reverted (PR #69, commits `6e06cb5`, `e6aac87`): refused ~half of real addresses | The guard here is a **lenient consistency check** (zip/settlement agreement), not a distance tolerance. |
| Google ToS: results meant for Google maps, limited caching | **Open decision D2.** Google is last-resort only (~5% of stops), behind a key-gated provider. |
| Privacy | Addresses leave our servers only to the configured geocoders. Google stage is off unless a key is set. |

## 3. Target pipeline

```
raw address
 ├─ 0. dedupe identical strings + geocode cache lookup
 ├─ 1. geocode raw, 5 in parallel (batches of 5)      -> found + consistent? done  (stage=raw)
 ├─ 2. rule-based parser on the failures only         -> cleaned address, parts, ordered query variants
 ├─ 3. re-geocode variants, same batches of 5         -> found + consistent? done  (stage=parsed)
 ├─ 4. Google Geocoding API on the still-failed       -> found + not partial/approximate? done (stage=google)
 └─ 5. user review queue, pre-filled with best guess  (stage=manual)
```

Every stop records the stage that resolved it, so the unresolved rate is measurable per stage.

### 3.1 Parallel batches (J2)
- `ThreadPoolExecutor(settings.GEOCODE_CONCURRENCY)` (default 5) inside the existing NDJSON stream; results are yielded as each
  completes (frontend progress contract unchanged: `{"stop": ..., "progress": {current,total}}`).
- Pipeline works on batches of 5 per stage: whole queue through stage 1, failures through parse -> stage 3 batches, remainder
  through Google. Alternative (per-stop waterfall) is simpler but gives worse progress reporting; batch-per-stage chosen.
- DB writes happen in the request thread (not workers) to avoid SQLite/connection issues.
- Provider exceptions/timeouts -> `geocode_status=failed` + readable `geocode_error`, never abort the batch (same as G1-AC4).

### 3.2 Parser (`backend/planner/addressparse/`)
Pure functions, each step records what it changed (`ParseResult.steps`), so results are explainable and testable.

1. **normalize.py** — Unicode NFC; fix mojibake (`õ`/`û` -> `ő`/`ű`); strip control chars/emoji; collapse whitespace;
   split on `, ; | \n`.
2. **noise.py** — remove from the address and keep in `removed[]` (never silently lost):
   dates (`1990.05.12`, `12/05/1990`, `szül.`, `született`), phone numbers (`+36`, `06 20`, `20/123-4567`), emails, URLs,
   parcel/tracking codes, honorifics/titles (`Dr.`, `özv.`, `ifj.`), delivery notes (`kapukód`, `csengő`, `hívjon`,
   `portás`, `postaláda`). **Safety rule:** a digit run is removed only if it matches a full date/phone shape and never when
   it directly follows a street type (that is a house number).
3. **postal.py** — 4-digit candidates validated against a bundled Magyar Posta zip -> settlement table. Zip vs house
   number decided by position (leading, or just before the city) and table membership. Budapest district forms
   (`XIII.`, `13. ker.`, `XIII. kerület`) -> `1x x0` zip via the existing `districts.py`. Zip/city conflict: zip wins if it
   is in the table. Missing zip: infer from settlement + street where the street table allows.
4. **settlement.py** — diacritics-folded match against the settlement table; `Bp.`/`Budapest` variants.
5. **street.py** — street-type lexicon (`u.`->`utca`, `krt.`->`körút`, `út`, `útja`, `tér`, `köz`, `sétány`, `fasor`,
   `rakpart`, `dűlő`, `lakótelep`, `hrsz`, ...). Fuzzy-correct against the street list of that zip/settlement
   (built offline from the OSM Hungary extract) with Damerau-Levenshtein + Hungarian phonetic folding
   (`ly`=`j`, `s`/`sz`/`zs`, `cs`, `ty`/`gy`/`ny` digraphs). Auto-correct only for a unique best match with a clear margin;
   otherwise keep the original and flag it.
6. **housenumber.py** — `12`, `12/A`, `12-14`, `12.`, `hrsz`; split staircase/floor/door (`A lh. II. em. 5. ajtó`) into a
   `unit` note (not geocodable, but shown to the biker).
7. **variants.py** — ordered query list with confidence: (1) full structured, (2) without unit, (3) `12/A`->`12`,
   (4) street spelling corrected, (5) zip + city + street without number. Variant 5 is street-level only: it is flagged and
   **never auto-accepted**.

Output: `ParseResult{cleaned, parts{zip,city,street,house,unit}, removed[], steps[], variants[], confidence}`.

### 3.3 Consistency guard (Must #2)
Accept a geocoder hit only if it lies within the parsed settlement's bounding box / a radius of the zip centroid
(`budapest.ZIP_CENTROIDS` for Budapest; settlement centroids elsewhere). Disagreement => treat as not found and move on.

### 3.4 Google stage (J5)
`components=country:HU|postal_code:<zip>`; reject `partial_match` and `location_type=APPROXIMATE`; key from env
(`GOOGLE_GEOCODING_API_KEY`); stage skipped when unset. Implemented as a provider on the G1 abstraction.

### 3.5 Review queue (J6)
Unresolved stops sorted by parse confidence; the parser's best variant is pre-filled with a candidates dropdown, one click to
accept. Reuses `update_stop_address` and the F-epic correction UI. Must keep `frontend/e2e/ux-15min.spec.ts` green.

## 4. Tasks (one task = one PR; suggested order J0 -> J1 -> J2 -> J3/J4 -> J5 -> J6 -> J7)

| ID | Title | Depends on | Size |
|----|-------|-----------|------|
| J0 | Golden corpus of messy Hungarian addresses + data tables (zip/settlement, street types, OSM street lists) | — | M |
| J1 | Provider seam + structured Nominatim query + configurable base URL (extends **G1**) | G1 | M |
| J2 | Concurrent batches of 5 in `_geocode_stream`, shared rate limiter, stage persistence (migration) | J1 | M |
| J3 | Parser core: normalize, noise, postal, settlement | J0 | L |
| J4 | Parser street/house/unit/variants + fuzzy street correction | J3 | L |
| J5 | Pipeline orchestration (stages 0-3) + consistency guard | J2, J4 | M |
| J6 | Google provider + stage 4 | J1, J5 | S |
| J7 | Review queue UI (pre-filled suggestion + candidates) | J5 | M |
| J8 | Self-hosted Nominatim (Hungary) deploy docs + `smoke_real_services` per-stage resolve rate | J2 | M |

### Model additions (J2, migration)
`DeliveryStop`: `geocode_stage` (`raw|parsed|google|manual`), `cleaned_address`, `parsed_parts` (JSON),
`address_candidates` (JSON list). All nullable/blank-default; no change to existing API fields.

## 5. Acceptance criteria (summary; each task file/PR names tests by AC id)

- **J-AC1** 5 requests are in flight at most/at least (fake provider with barrier): batches of 5, never more than `GEOCODE_CONCURRENCY`.
- **J-AC2** With the public Nominatim URL configured the limiter still enforces 1 req/s globally across workers.
- **J-AC3** A failed raw address goes through the parser and the **same batch size** is used for the re-geocode.
- **J-AC4** Google provider is called only for stops that failed stages 1 and 3, and never when the key is unset.
- **J-AC5** Manual queue contains only stops that failed all automatic stages; each carries a pre-filled suggestion.
- **J-AC6** Noise removal: birth dates, phones, emails, notes are removed and listed in `removed[]`; **a valid house number is never removed** (property test over the corpus).
- **J-AC7** Parser is idempotent: parsing an already-clean address returns it unchanged.
- **J-AC8** A hit outside the parsed zip/settlement area is rejected (Must #2), including in mock mode.
- **J-AC9** Provider timeout/exception on one stop leaves the rest of the batch intact.
- **J-AC10** `E2E_MOCK` pipeline is deterministic and offline; `ux-15min.spec.ts` stays green.

## 6. Test plan

- **U** golden corpus (200+ messy addresses: birth dates, phones, missing/wrong zip, `u.`/`utca`, Roman-numeral districts,
  `12/A 3/5`, mojibake) with expected parts; per-step unit tests; property tests (no house-number loss, idempotence).
- **U** pipeline with a fake geocoder: stage order, batching, Google last, caching/dedupe.
- **A** `geocode_stops` end to end (stub provider via `override_settings`): stage persisted, progress stream intact.
- **E** existing wizard flow + a spec with a `nocity`/messy row resolving without manual fix.
- Never call Nominatim/Google/ORS from automated tests (README rule). Real-service coverage lives in
  `smoke_real_services`, extended in J8 to print the per-stage resolve rate on a real sample.

## 7. Success metric

On a real-style 600-700 address file: manual-fix share reported per stage by the smoke command; target set after the
first J0 corpus run (baseline = today's raw-Nominatim failure rate), with the geocode step well inside the 15-minute budget.

## 8. Open decisions (raise before J5/J6; do not guess)

1. **D1 Nominatim hosting:** self-host the Hungary extract (recommended; required for real parallelism) vs stay on the
   public server at 1 req/s (J2 still works, just not faster). Hosting cost/where (Render is likely too small).
2. **D2 Google:** accept ToS limits (non-Google map, caching) and sending unresolved addresses to Google; who provides the key.
   If rejected, stage 4 is dropped and the review queue follows stage 3.
3. **D3 Street auto-correct:** silent fix at high confidence (recommended, always visible in review) vs suggest-only.
4. **D4 Data licensing:** Magyar Posta zip table and OSM street lists — confirm the licences allow bundling (OSM = ODbL, attribution).

## 9. Risks

| Risk | Mitigation |
|------|-----------|
| Parser "fixes" an address into a wrong but plausible one (violates Must #2) | Consistency guard + variant 5 never auto-accepted + `steps[]` audit trail + auto-correct only on unique clear-margin match |
| Over-aggressive noise stripping deletes a real house number | Position rule (never after a street type), full-shape matching only, property test J-AC6 |
| Self-hosted Nominatim ops burden | Setting-driven URL; public fallback with limiter; J8 docs |
| Street tables go stale | Rebuild script in J0, documented refresh cadence |
