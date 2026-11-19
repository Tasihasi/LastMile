"""Smoke test of the REAL external services (no mock): Nominatim geocoding and ORS routing.

Enforces the whole-app must conditions that mock-based tests cannot see:
  M1  addresses are geocoded to where they really are;
  M2  routes are truly optimized and follow roads (not straight lines between stops).

Run: ``python manage.py smoke_real_services`` with ORS_API_KEY set and E2E_MOCK unset.
Exit code != 0 on any failure. CI runs it before the e2e job (see .github/workflows/ci.yml).
"""

from types import SimpleNamespace

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from planner import geocoder, optimizer, timing
from planner.budapest import haversine_km

# (address as a planner would type it, (lat, lng) of THAT HOUSE's own OpenStreetMap node). Guarantee: a
# pinned address is within 2 m of its house; an address OSM cannot pin that precisely is REFUSED with a
# reason, never pinned somewhere else. The cases used to land 7-11 km away (same-named streets in other
# districts) or on the street/building instead of the house.
GEOCODE_CASES = [
    ("Kazinczy utca 14 Budapest", (47.49693, 19.06331)),
    ("1075 Budapest, Kazinczy utca 14", (47.49693, 19.06331)),
    ("Gyulai Pal utca 2 Budapest", (47.49527, 19.06784)),
    ("Karoly korut 3 Budapest", (47.49525, 19.05958)),
    ("Marcius 15 ter 7 Budapest", (47.49157, 19.05297)),
    ("Futo utca 37 Budapest", (47.48627, 19.07447)),
]
GEOCODE_TOLERANCE_KM = 0.002  # 2 m
MIN_PINNED = 3  # of the cases above (OSM data decides which can be pinned within 2 m; the rest are refused)
# Must NOT be pinned: a typo'd street (really "Futo") or a missing house number is a failure, never a guess.
MUST_FAIL = ["Futyo utca 37 Budapest", "Vamhaz korut Budapest"]


class Command(BaseCommand):
    help = "Smoke-test real geocoding and real road routing (fails on mock, wrong spots, straight lines)."

    def handle(self, *args, **options):
        failures = []
        if settings.E2E_MOCK:
            raise CommandError("E2E_MOCK is on: the smoke test must run against the real services.")
        key = settings.ORS_API_KEY or ""
        if not key or key.startswith(("e2e", "test")):
            raise CommandError("ORS_API_KEY is missing or a placeholder: real routing cannot be checked.")

        stops = self._geocoding(failures)
        if len(stops) >= 3:
            self._routing(stops, failures)
        else:
            failures.append(f"routing: only {len(stops)} stops geocoded, cannot test routing")

        if failures:
            raise CommandError("Real-services smoke FAILED:\n  - " + "\n  - ".join(failures))
        self.stdout.write(self.style.SUCCESS("Real-services smoke passed (real geocoding, real road routing)."))

    def _geocoding(self, failures):
        stops, seen = [], set()
        for address, truth in GEOCODE_CASES:
            result = geocoder.geocode_address(address)
            if result is None:
                self.stdout.write(f"geocode {address!r}: refused ({geocoder.last_failure_reason()})")
                continue
            km = haversine_km(result, truth)
            self.stdout.write(
                f"geocode {address!r}: {result[0]:.5f},{result[1]:.5f} ({km * 1000:.1f} m from the house)"
            )
            if km > GEOCODE_TOLERANCE_KM:
                failures.append(f"geocoding: '{address}' pinned {km * 1000:.1f} m from its house {truth} (limit 2 m)")
            if result == geocoder._mock_geocode(address):
                failures.append(f"geocoding: '{address}' equals the mock coordinates (mock in use?)")
            if truth not in seen:  # the zip variant repeats a location, keep the stop list distinct
                seen.add(truth)
                stops.append(SimpleNamespace(id=len(stops) + 1, lat=result[0], lng=result[1]))
        pinned = len(stops)
        if pinned < MIN_PINNED:
            failures.append(
                f"geocoding: only {pinned} of {len(GEOCODE_CASES)} addresses could be pinned (need {MIN_PINNED})"
            )
        for address in MUST_FAIL:
            result = geocoder.geocode_address(address)
            if result is not None:
                failures.append(f"geocoding: '{address}' must not be pinned but got {result}")
            else:
                self.stdout.write(f"geocode {address!r}: refused ({geocoder.last_failure_reason()})")
        return stops

    def _routing(self, stops, failures):
        depot = timing.DEPOT
        ids = optimizer.optimize_route(stops, depot=depot)
        by_id = {s.id: s for s in stops}
        if sorted(ids) != sorted(by_id):
            failures.append(f"routing: optimizer returned {ids}, expected each of {sorted(by_id)} once")
            return
        ordered = [by_id[i] for i in ids]
        route = optimizer.get_route_details(ordered, depot=depot)
        if not route:
            failures.append("routing: no route details returned")
            return

        coords = route["geometry"]["coordinates"]
        waypoints = len(ordered) + 2
        self.stdout.write(
            f"route: {len(coords)} geometry points for {waypoints} waypoints, "
            f"{route['total_distance'] / 1000:.1f} km, {route['total_duration'] / 60:.0f} min"
        )
        if len(coords) < 10 * waypoints:
            failures.append(f"routing: {len(coords)} geometry points for {waypoints} waypoints = straight lines")

        path = [depot, *[(s.lat, s.lng) for s in ordered], depot]
        straight_km = sum(haversine_km(a, b) for a, b in zip(path, path[1:], strict=False))
        km = route["total_distance"] / 1000
        if not straight_km * 0.99 <= km <= straight_km * 3:
            failures.append(f"routing: road distance {km:.1f} km vs straight line {straight_km:.1f} km is implausible")

        original = optimizer.get_route_details(stops, depot=depot)
        if original and route["total_duration"] > original["total_duration"]:
            failures.append(
                f"routing: optimized order ({route['total_duration']} s) is slower than the input order "
                f"({original['total_duration']} s)"
            )
