# Production Readiness Checklist

> **Status: NOT production-ready.** This is currently a learning/portfolio MVP.
> Everything in **Blockers** must be done before deploying to a real company's
> production environment. **Hardening** items should follow soon after.
>
> Created: 2026-06-28. Audited against `ci.yml` and `config/settings.py` as of this date.

---

## 🔴 Blockers — MUST be done before any company production deployment

These are real risks that no automated scanner will catch. They are the actual
reasons this app is not yet safe for a company handling real delivery data.

- [ ] **Real authentication (passwords + Google).**
  Today `/api/auth/login/` creates a user + token from *just a username + role*.
  Anyone who types a username is logged in, and can self-select the `planner`
  role to see and manage **everyone's** routes.
  - File: `backend/planner/views.py` (login view), `LoginScreen.tsx`.
  - **Detailed implementation plan:** `claude_exec_plan/add_auth.md`
  - **Stack:** `dj-rest-auth` + `django-allauth` (covers email/password login,
    registration, password reset, *and* Google OAuth in one library; plugs into
    the existing DRF `TokenAuthentication`).
  - **Also needs:** an email provider for password reset (Brevo/Resend free tier)
    and a Google Cloud OAuth project (Client ID/Secret + redirect URIs).
  - **Effort:** ~2–4 days. Ship in two PRs: (1) email/password + reset first
    (the actual security fix), (2) Google OAuth as a follow-up convenience.
  - **Ordering:** do this *with or after* the SQLite→Postgres move (allauth adds
    tables — avoid migrating auth data twice).

- [ ] **Switch SQLite → PostgreSQL.**
  SQLite is single-file with no real concurrent-write support. Multiple
  bikers/planners writing at once will hit lock errors or corruption.
  - File: `backend/config/settings.py` (`DATABASES`).

- [ ] **Lock down role assignment.**
  Role (`biker` / `planner`) must not be self-selectable at login. Planners
  should be provisioned/promoted by an admin, not chosen by the user.

- [ ] **PII handling for uploaded delivery data.**
  Uploaded files contain real recipient names, addresses, and phone numbers and
  currently sit unmanaged in `backend/media/uploads/` with no cleanup and no
  per-user access scoping. Define: retention/cleanup policy, access control on
  uploaded files, and confirm this is acceptable under the company's data
  agreement (GDPR — this is Hungary/EU data).

- [ ] **Confirm `DEBUG=False` in production.**
  `DEBUG` defaults to `True` (`settings.py:28`). A missing `DEBUG=False` env var
  leaks full stack traces and settings to users. Either default it to `False` or
  add a deploy-time guard that fails the boot if `DEBUG` is true in prod.

---

## 🟡 Hardening — do soon after launch

- [ ] **Token expiry / rotation.**
  DRF `TokenAuthentication` tokens never expire. Add expiry/rotation (or move to
  JWT / session-based auth with sensible lifetimes).

- [ ] **Tighten CORS + `ALLOWED_HOSTS`.**
  Verify production env vars (`CORS_ALLOWED_ORIGINS`, `ALLOWED_HOSTS`) are set to
  exact company domains, not defaults.

- [ ] **Rate limiting** on auth + upload + geocode endpoints (DRF throttling).

- [ ] **File upload validation** beyond size: validate content type / parse
  safely (XML parsing — confirm no XXE; `xml.etree` is used in `parsers.py`).

- [ ] **Backups** for the (Postgres) database.

- [ ] **Error monitoring** (e.g. Sentry free tier) so production errors surface.

---

## 🛠️ CI security tooling — cheap wins, add to `.github/workflows/ci.yml`

> NOTE: `CLAUDE.md` previously claimed `pip-audit`, `npm audit`, and coverage
> reporting already ran in CI. They did **not**. As of this PR, static security
> tooling (`check --deploy`, gitleaks, Trivy, Dependabot) is now actually wired
> into `ci.yml`; CLAUDE.md's CI/CD section has been corrected to match reality.

Security tools split into **two tiers** by difficulty. Static tools just read
files (easy, run on every push). DAST tools must boot + attack a live app
(hard, slow, noisy — run on a schedule, not on every commit).

### Tier 1 — Static scans, add to main CI now (every push/PR, all free)

- [x] **`python manage.py check --deploy`** — the production-settings audit
  (SECRET_KEY, DEBUG, cookies, HSTS). _Added to the `backend` job in `ci.yml`,
  runs with `DEBUG=False` + a placeholder `SECRET_KEY`, non-blocking
  (`continue-on-error`)._
- [x] **Secret scanning — `gitleaks`** (official GitHub Action). Scans code +
  full git history. _Added as a `security` job (`gitleaks/gitleaks-action@v2`,
  `fetch-depth: 0`), non-blocking._
- [x] **`Trivy`** (`aquasecurity/trivy-action`, `fs` mode) — scans
  `requirements.txt`, `package-lock.json`, and source for known CVEs in one
  pass (covers both Python + npm, so it replaces `pip-audit` + `npm audit`).
  _Added to the `security` job (HIGH,CRITICAL, ignore-unfixed), non-blocking.
  TODO: pin `@master` to a release tag once baseline reviewed._
- [x] **GitHub native — Dependabot** version updates. _Added `.github/dependabot.yml`
  (pip + npm + github-actions, weekly, grouped). Dependabot **alerts** are a
  separate repo-settings toggle — enable in GitHub UI._
- [ ] **SAST — `Semgrep`** (good Django + React rulesets) or `Bandit`
  (Python-only, simpler). Optional next step after the above.
- [ ] **CodeQL** (one workflow file) — GitHub native, not yet added.

**Suggested minimum starter set:** `check --deploy` + gitleaks + Trivy +
Dependabot. ✅ **Done in this PR.** Scanners start non-blocking
(`continue-on-error: true`); review the baseline, then remove the flag to gate.

### Tier 2 — DAST (dynamic scans), separate scheduled workflow, do LATER

> ⚠️ Do **NOT** gate every deploy on these — too slow and noisy. Run as a
> separate **scheduled (`cron`) or manual (`workflow_dispatch`)** workflow, and
> ideally **after real auth lands** (most endpoints need a token — an
> unauthenticated scan only sees the login surface). Reuse the existing Playwright
> `webServer` pattern to boot the stack in CI.

- [ ] **Wapiti** (black-box CLI) — easier of the two. Point at the running URL
  with an auth header; tests SQLi / XSS / file disclosure. Medium effort.
- [ ] **OWASP ZAP** — more powerful, heavier. Baseline scan
  (`zaproxy/action-baseline`) is approachable; a full *authenticated* active
  scan is real config work (auth context + token injection). Do after Wapiti.
- [ ] Budget ~1–2 days to set up authenticated DAST properly (mostly debugging
  auth + triaging false positives).

> ⚠️ Green security badges do **not** mean production-ready. The Blockers above
> (auth, Postgres, PII) are the things that would actually bite a company, and no
> free scanner will flag them.

---

## Reference — current production security that IS already in place

(So we don't redo these — see `config/settings.py`.)

- HTTPS enforcement when `DEBUG=False`: `SECURE_SSL_REDIRECT`, HSTS (1yr,
  subdomains, preload), `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
  `SECURE_PROXY_SSL_HEADER`.
- `SECRET_KEY` required (raises) when `DEBUG=False`.
- File upload size limit: 10 MB.
- Token auth + `IsAuthenticated` default permission on DRF.
- DB indexes on hot columns; N+1 query elimination.
