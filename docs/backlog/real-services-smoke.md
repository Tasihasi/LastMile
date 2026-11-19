# Real-services smoke and findings log (2026-11-19)

Findings reported by the planner after PR #67, logged here and covered by `python manage.py smoke_real_services`
(CI job **Real Services Smoke**; the **E2E** job `needs` it and the Production Smoke job, so no e2e test runs before both pass).

| # | Finding | Cause | Status |
|---|---------|-------|--------|
| 1 | Not real geocoding: addresses scattered at random points | `E2E_MOCK` geocoder hashed the address to a random point; a stale dev server kept running that mock | Mock now places an address in its postal code's area; smoke runs with the mock OFF and fails if a result equals the mock coordinates |
| 2 | Addresses in the wrong spot (real geocoder) | Nominatim's first hit is often a same-named street in another district: "Kazinczy utca 14" 8.9 km off, "Kiraly utca 13" 7.5 km, "Gyulai Pal utca 2" 11.3 km | Several candidates are requested; postcode match wins, else nearest the postal-code centroid / depot. Smoke asserts every case is within 600 m of its real spot |
| 3 | Routes are simple straight lines, not true optimization | Mock optimizer = angle sort + straight segments; a failed ORS directions call was swallowed and the map fell back to lines | Offline optimizer is nearest neighbour + 2-opt; optimize returns 502 when road geometry fails; smoke asserts real VROOM order, road geometry (>= 10 points per waypoint), plausible road distance, optimized no slower than input order |

Known limit: an address Nominatim cannot match at all (e.g. unaccented "Futyo utca 37", really "Fűtő utca") is reported as failed, never pinned.

CI needs the repository secret `ORS_API_KEY` (a real openrouteservice key). Without it the real-services job fails on purpose.

## Precision (house level)
A pin is accepted only if the geocoder result carries the requested **house number** (ranges like `2-4` count for `2`);
a street-level hit, a missing house number, a wrong postal code or a typo'd street is a **failure with a reason**
(`geocode_error`), never a guess. Address points / buildings win over shops and bars; several POIs of one number use
their median. Without a postal code the postcode group nearest the depot is used, so send postal codes where possible.
Smoke tolerance: 60 m from the house on 6 real addresses, and two addresses that must be refused.

Known limit: where OSM has no address point for a number (e.g. Kiraly utca 13: only shops/bars, spread ~130 m) the pin
is the median of those POIs, up to ~60-100 m from the building. A second data source would be needed to do better.
