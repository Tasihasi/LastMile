# Real-services smoke and findings log (2026-11-19)

`python manage.py smoke_real_services` (CI job **Real Services Smoke**; the **E2E** job `needs` it and the Production Smoke
job, so no e2e test runs before both pass) checks the REAL services, no mock:

- **Geocoding:** five real addresses *with postal code* (as in the daily files) must land within 100 m of their house and
  must not equal the offline-mock coordinates. The real geocoder is the original one (Nominatim, first hit).
- **Routing:** real VROOM order, road geometry (>= 10 points per waypoint), plausible road distance, optimized order no
  slower than input order.

| # | Finding | Cause | Status |
|---|---------|-------|--------|
| 1 | Addresses scattered at random points | `E2E_MOCK` geocoder hashed the address to a random point; a stale dev server kept running the mock | Mock now places an address inside its postal code's area |
| 2 | Routes are straight lines, not optimization | Mock optimizer = angle sort + straight segments; a failed ORS directions call was swallowed | Offline optimizer is nearest neighbour + 2-opt; optimize returns 502 if road geometry fails |
| 3 | Addresses in the wrong spot | Real geocoder takes Nominatim's first hit; an address WITHOUT postal code ("Kazinczy utca 14 Budapest") can resolve to a same-named street in another district | Open for city-only addresses: type the postal code. Stricter pinning (house-number match, 2 m limit) was tried and reverted because it refused about half of real addresses (see git history of PR #69) |

CI needs the repository secret `ORS_API_KEY` (a real openrouteservice key). Without it the real-services job fails on purpose.
