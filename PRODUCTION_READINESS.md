# Production Readiness

Tracks the work required to take LastMile from a demo/portfolio app to a
production-grade deployment. Items are grouped into tiers by risk and urgency.

**Tier 1 — Safety (secrets & credential hygiene)** is the prerequisite for
everything else: a leaked credential is the one mistake you cannot take back.
Tier 1 is implemented; Tiers 2–3 are scoped for follow-up.

## Status legend

| Mark | Meaning |
|------|---------|
| ✅ | Implemented and verified |
| 🔜 | Planned (scoped, not yet built) |
| ⚪ | Idea / backlog |

---

## Tier 1 — Secrets & credential hygiene ✅

Goal: make it **structurally hard to commit a secret**, and catch it in CI if a
local guard is ever bypassed or missing. Defense in depth — local hook + CI gate
+ ignore rules + a single documented source of truth for env vars.

### What was added

| # | Change | File | Status |
|---|--------|------|--------|
| 1.1 | Local secret-scanning pre-commit hook (gitleaks) | `.pre-commit-config.yaml` | ✅ |
| 1.2 | Private-key, large-file, and whitespace guards | `.pre-commit-config.yaml` | ✅ |
| 1.3 | Shared gitleaks ruleset + placeholder allowlist | `.gitleaks.toml` | ✅ |
| 1.4 | CI secret-scan gate on push/PR (history-wide) | `.github/workflows/secret-scan.yml` | ✅ |
| 1.5 | Hardened env ignore rules (no `.env*` can be staged) | `.gitignore` | ✅ |
| 1.6 | Complete, documented env template | `backend/.env.example` | ✅ |
| 1.7 | Developer setup instructions | `README.md`, this file | ✅ |

### 1.1–1.2 — Pre-commit hooks

`.pre-commit-config.yaml` runs on every `git commit` once installed and blocks
the commit if any staged change contains:

- a hardcoded secret (gitleaks, default ruleset + this repo's config),
- a private key (`detect-private-key`),
- a file larger than 5 MB (`check-added-large-files`).

It also fixes trailing whitespace / missing final newlines so formatting noise
never masks a real diff.

**One-time setup per clone:**

```bash
pip install pre-commit      # already in backend/requirements-dev.txt
pre-commit install          # installs the git hook
```

**Scan the whole repo on demand:**

```bash
pre-commit run --all-files
```

### 1.3 — gitleaks config

`.gitleaks.toml` extends the built-in ruleset and allowlists the project's known
non-secret placeholders so the scan stays signal-only (no false positives):

- `backend/.env.example` and `frontend/.env.development` (templates),
- the `django-insecure-…` dev fallback key in `settings.py`,
- CI test placeholders (`test-key`, `e2e-mock-key`) and the env-template
  placeholders.

The same config is used by the local hook and CI, so results are identical in
both places.

### 1.4 — CI secret-scan gate

`.github/workflows/secret-scan.yml` installs gitleaks and runs a **history-wide**
scan (`fetch-depth: 0`) on every push to `main`/`production`, every pull request,
and on manual dispatch. The job fails the build if a secret is found — this is
the backstop for any contributor who hasn't installed the local hook.

### 1.5 — Hardened ignore rules

`.gitignore` now refuses every `.env` variant by default and re-allows only the
two non-secret templates:

```gitignore
.env
.env.*
*.env
!.env.example
!.env.development
```

This means a real `backend/.env`, `.env.local`, or `prod.env` cannot be staged
by accident, while the committed templates remain tracked.

### 1.6 — Complete env template

`backend/.env.example` previously documented only `ORS_API_KEY`. It now documents
every variable `settings.py` reads — `DEBUG`, `SECRET_KEY` (with a generation
command), `ALLOWED_HOSTS`, `RENDER_EXTERNAL_HOSTNAME`, `CORS_ALLOWED_ORIGINS`,
`ORS_API_KEY`, `E2E_MOCK` — with placeholders only. Developers copy it to
`backend/.env` instead of improvising and risking a hardcoded value.

### Existing baseline (already in place, confirmed)

These were already correct and are relied on by Tier 1:

- `SECRET_KEY` is required (raises) when `DEBUG=False`; the insecure fallback is
  dev-only — `backend/config/settings.py`.
- `ORS_API_KEY` / `SECRET_KEY` are read from the environment, never hardcoded.
- No secret has ever been committed (verified — see below).

### Verification (2026-06-28)

Run on branch `feature/git-secrets-checks` with gitleaks v8.30.1:

- `gitleaks dir` (working tree) → **no leaks found** (exit 0).
- `gitleaks git` (102 commits, full history) → **no leaks found** (exit 0).
- Negative control: a planted `ghp_…` token was **detected** (exit 1),
  confirming the guard is active, not vacuously passing.
- `git ls-files` shows only `backend/.env.example` and
  `frontend/.env.development` matching `*.env*` — no real env file tracked.

---

## Tier 2 — Application hardening 🔜

Scoped for follow-up. Not blocking, but needed before real traffic.

- 🔜 **Rate limiting / throttling** on auth and upload endpoints (DRF
  throttles) to blunt abuse of the free external-API quotas.
- 🔜 **Real authentication** — the demo uses passwordless username+role login.
  Production needs real credentials and per-user authorization review.
- 🔜 **Upload validation** beyond the 10 MB size cap: content-type allowlist,
  row-count ceiling, and parser hardening against malformed XML/CSV.
- 🔜 **Structured error handling** — ensure no stack traces or internal detail
  leak to clients when `DEBUG=False`; add a DRF exception handler.
- 🔜 **Dependency audit in CI** — `pip-audit` (backend) and `npm audit`
  (frontend) as non-blocking-then-blocking gates.

## Tier 3 — Scale & operations ⚪

- ⚪ **PostgreSQL** instead of SQLite (concurrency, durability).
- ⚪ **Backups** and migration/runbook documentation.
- ⚪ **Monitoring & alerting** — error tracking (e.g. Sentry), uptime checks.
- ⚪ **Secret rotation** policy and a secrets manager for production env vars.
- ⚪ **Log review** — confirm no PII (recipient names/phones) is logged.

---

## Change log

- **2026-06-28** — Tier 1 (secrets & credential hygiene) implemented on
  `feature/git-secrets-checks`: gitleaks pre-commit hook, CI secret-scan gate,
  shared gitleaks config, hardened `.gitignore`, complete `.env.example`. Repo
  verified clean (working tree + full history). Tiers 2–3 scoped.
