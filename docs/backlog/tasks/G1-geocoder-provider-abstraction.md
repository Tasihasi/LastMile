# G1 — Geocoder provider abstraction

**Email §6** · **P1** · **Depends on:** — · **Size:** M

## Goal
Make geocoding swappable (Nominatim today; candidates from the RouteXL comparison tomorrow) behind one interface so G2 can benchmark providers and I1 can configure them without code changes.

## Context
`backend/planner/geocoder.py` — module-level functions, Nominatim hard-coded, 1 req/s limiter, `E2E_MOCK` branch.

## Scope
- `class GeocoderProvider(Protocol): name; geocode(address, *, zip=None) -> GeocodeResult | None` where `GeocodeResult = {lat, lng, confidence?: float, matched_address?: str, raw?: dict}`.
- Implementations: `NominatimProvider` (current behaviour), `MockProvider` (current mock). Registry + `settings.GEOCODER_PROVIDER` (env), default `nominatim`.
- `geocode_address()` stays as the public façade → no caller changes needed.
- Provider receives postal code as a hint when available (accuracy lever for G2).

## Acceptance criteria
- **G1-AC1** Existing `GeocoderTest` passes unchanged.
- **G1-AC2** Setting `GEOCODER_PROVIDER=mock` yields deterministic coords; unknown provider name → clear error at startup (`manage.py check`).
- **G1-AC3** A fake provider registered in a test is used by `geocode_stops` end-to-end (proves the seam).
- **G1-AC4** Provider exceptions/timeouts yield `geocode_status=failed` with a readable `geocode_error`, never a 500 or an aborted batch.
- **G1-AC5** Result carries `confidence` when the provider supplies it and it is persisted/available for review (nullable field optional, not required now).

## Test plan
- U: extend `GeocoderTest` — AC1, AC2, AC4 (mock `requests.get` raising `Timeout`).
- A: AC3 using a stub provider via `override_settings` + registry.
- `python manage.py check --fail-level WARNING` — AC2.

## Out of scope
New real providers (decided in G2), admin UI for keys (I1).
