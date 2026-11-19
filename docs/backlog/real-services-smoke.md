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

## Precision: within 2 m (`GEOCODE_MAX_ERROR_M`, default 2)
A pin is accepted only if all of this holds, otherwise the stop **fails with a reason** (`geocode_error`), never a guess:
1. the result carries the requested **house number** (ranges like `2-4` count for `2`);
2. it is a **map point**, not a building outline or area (Nominatim's bounding box tells: ~7 m = point, 28-220 m = outline);
3. OSM address points beat shops/bars; the chosen points must **agree within 2 m**;
4. postal code (if typed) matches; without one the postcode group nearest the depot wins.

Smoke (`smoke_real_services`): pinned addresses must be within 2 m of their house's OSM node, at least 3 of 6 real
addresses must be pinnable, and a typo'd street / missing house number must be refused.
Result on 2026-11-19: 3 of 6 pinned (0.9-2 m), 3 refused (Gyulai Pal utca 2: only a 143 m building outline in OSM;
Karoly korut 3: two shops 17 m apart; Kazinczy utca 14 typed *with* zip: two nodes 4 m apart).

Limits: OSM node positions are mappers' clicks, so "within 2 m" means 2 m of the OSM point, not a surveyed door. A
2 m guarantee refuses many real addresses (roughly half of this sample); loosen with env `GEOCODE_MAX_ERROR_M`
(e.g. 25) or add a second data source / manual pin placement for refused stops.
