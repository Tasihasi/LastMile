# I1 — Admin page for external-service API keys

**Email "+ later"** · **P2** · **Depends on:** G1 · **Size:** L

## Goal
One admin-only page where services (storage, geocoding, route optimization, database) can be swapped/renewed by pasting an API key — no developer needed. Total budget for all services: 20–80k HUF/month.

## Scope
- New role `admin` (or Django `is_superuser`) — planners must NOT see it.
- Model `ServiceConfig(kind: storage|geocoding|routing|database, provider, api_key_encrypted, base_url?, enabled, updated_at, updated_by)`; keys **encrypted at rest** (Fernet, key from env), never returned in clear by the API (masked `••••abcd`).
- Endpoints `GET/PUT /api/admin/services/` (admin-only). Runtime providers (G1 registry, optimizer) read from DB, fall back to env vars.
- "Test connection" button per service (cheap call), result shown.
- Database switching is **display/config only** in v1 (document; do not hot-swap DB connection).

## Acceptance criteria
- **I1-AC1** Planner/biker → 403 on the endpoints; page hidden for them.
- **I1-AC2** GET never contains full key; PUT with masked placeholder leaves the stored key unchanged.
- **I1-AC3** DB column is not plaintext (test reads raw value ≠ key).
- **I1-AC4** Changing geocoding provider in the page changes which provider `geocode_address` uses on the next call, no restart (test with fake providers).
- **I1-AC5** Failed "test connection" returns a readable error, doesn't save as enabled.
- **I1-AC6** Changes are audit-logged (who/when/which service, never the key).
- **I1-AC7** Missing DB config → falls back to env behaviour (existing deployments unaffected).

## Test plan
- A: AC1–AC7 in `AdminServicesAPITest`.
- E: `admin-settings.spec.ts` — admin sees page, planner doesn't; masked key display.
- Security review: run `/security-review` on the PR.
