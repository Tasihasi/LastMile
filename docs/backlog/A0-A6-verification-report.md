# Verification report: branch `feature/a6-minimal-zone-splitting` (A0–A6)

Date: 2026-11-17 · Reviewer role: PO (acceptance against Gergő's email §1 and the task files)
Scope: A0–A6 (zones, zip-atomic split, validator, move-zip override, zone-first allocation, minimal splitting).

## 1. Verdict

**Not ready to merge as a complete A5/A6.** A0–A4 meet their acceptance criteria. A5 and A6 are correct as library code
but cannot be reached from the product, and their default behaviour contradicts parts of the email.

## 2. Evidence

| Check | Result |
|---|---|
| `ruff check` / `ruff format --check` | Clean (55 files) |
| `manage.py test` | 264 tests, all pass |
| `npm run lint`, `npx tsc -b`, `npm run build` | Pass (chunk-size warning only) |
| Playwright `clustering` + `move-zip` | 6/6 pass (HTML reporter `EPERM` on `playwright-report` is environmental) |
| Manual probes on `REALISTIC_DAY` (231 stops, 3–6 bikers, windows 110–420 min) | Zip integrity held in every run; see findings for the rest |

Not verified: the full e2e suite (only the two A-related specs were run), and the manual-script (M) steps, which need a
running dev stack with a browser session.

## 3. Task-by-task

### A0 — Fixtures and spike: PASS
Deterministic generator, `REALISTIC_DAY` with zip 1054 at 56 stops (> 48 capacity, AC2), spike report committed.

### A1 — Zone config: PASS
16 zones / 34 zips, validator, `GET /api/zones/` planner-only, placeholder warning hook in `apps.py`.

### A2 — Zip-atomic distribution: PASS
Default and `assignments` paths use `cluster_zip_atomic`. No zip split across routes in any probe. `oversized_zips` and
`unzipped_stop_ids` returned.

### A3 — Conflict validator and banner: PASS
`zip_conflicts` in session, cluster and move-stop responses; banner covered by e2e (appears on split, clears on resolve).

### A4 — Move whole zip / zone: PASS
AC1–AC8 have named tests (validation, in-progress block, permissions, atomicity, excluded stops). e2e passes.
Note: like `move_stop`, only the moved stops lose `sequence_order`; routes lose geometry/duration. Consistent with the spec's
"reuse move_stop".

### A5 — Zone-first allocation: FAIL (acceptance in practice)
Unit and API tests pass, but see findings F1–F4.

### A6 — Minimal splitting: CONDITIONAL
Correct on small instances (brute-force test), but see F1 and F5.

## 4. Findings

**F1 — A5/A6 unreachable from the product (blocker).**
The zone-first path only runs when every assignment carries `window_minutes` and has no zip/district lock. The frontend
never sends `window_minutes` or `multiplier`. A5's dependencies B1/B2 (depot start/return times) are not on the branch.
Result: Gergő's steps 1 and 2 (fill zones by available time, then break as few zones as needed) never execute in real
use; the default remains A2. The A6 e2e passes only by calling the API directly with `window_minutes: 60`.

**F2 — Windows silently ignored (high).**
Mixed payloads (some bikers with a window, some without, or a window plus a zip/district lock) fall back to the old path
with no warning or error.

**F3 — Empty routes (high).**
The allocator fills the first biker to the brim. Probes: 4 bikers × 360 min → two routes at 0 min; 3 × 420 → one at 0 min.
The view creates a sub-route per cluster, so empty sub-routes would be created. This contradicts "most fully use the
available time" across the requested bikers.

**F4 — Overrun used as normal capacity (medium).**
Routes are packed up to window × 1.075 (e.g. 449.6 of 420 min). The email describes 7.5 % as a tolerance negotiated with
the courier, not a planning target. Planners will see most routes in overtime.

**F5 — "Fewest zones broken" not guaranteed at realistic sizes (medium).**
Exact search only while routes^zips ≤ 5000, else greedy. Probe: 6 bikers × 110 min → greedy left 2 over-capacity routes,
exact left 1. AC5 is only tested at ≤5 zones / ≤3 routes. A day with ≥5 bikers and ≥6 unassigned zips exceeds the limit.

**F6 — Oversize-zip placement deviates from spec (low).**
Spec: leave it whole in the least-loaded route. Implementation minimises (over-capacity routes, zones broken, total load).

**F7 — Repo hygiene (low).**
- `CHANGELOG.md`: 312 changed lines vs `main`, 14 real; the rest is line-ending churn. Violates "no unrelated diffs".
- `.gitignore` modified and `docs/backlog/` untracked (this report included).

## 5. Required before merge

1. Provide a way to supply time windows (B1 stub, config, or UI), or mark A5/A6 "API-only" in the backlog and PR text.
2. Prevent empty routes: spread load or drop empty clusters before creating sub-routes.
3. Pack to the base window; use the 7.5 % only as overflow and flag routes that rely on it.
4. Reject or warn on mixed window/lock payloads.
5. Make A6 exact for realistic sizes (add a test above the 5000 limit) or state the guarantee precisely.
6. Restore CHANGELOG line endings.

## 6. Open product questions
- Does the PO accept A5/A6 shipping before B1/B2, given the dependency declared in the task files?
- Should the overrun ever be used by the allocator, or only reported (B2)?
- Minimum routes: must every requested biker receive stops?
