"""Smoke test of the REAL external services (no mock): Nominatim geocoding and ORS routing.

Enforces the whole-app must conditions that mock-based tests cannot see:
  M1  addresses are geocoded to where they really are;
  M2  routes are truly optimized and follow roads (not straight lines between stops).

Run: ``python manage.py smoke_real_services`` with ORS_API_KEY set and E2E_MOCK unset.
Exit code != 0 on any failure. CI runs it before the e2e job (see .github/workflows/ci.yml).
"""

import time
from types import SimpleNamespace

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from planner import geocoder, optimizer, timing
from planner.budapest import haversine_km

# (address as a planner would type it, true (lat, lng) from OpenStreetMap) - the first three are the
# addresses that used to land in the wrong place (same-named streets in other districts).
GEOCODE_CASES = [
    ("Kazinczy utca 14 Budapest", (47.4969, 19.0633)),
    ("Kiraly utca 13 Budapest", (47.4986, 19.0591)),
    ("Gyulai Pal utca 2 Budapest", (47.4952, 19.0678)),
    ("Karoly korut 3 Budapest", (47.4953, 19.0594)),
    ("1075 Budapest, Kazinczy utca 14", (47.4969, 19.0633)),
]
GEOCODE_TOLERANCE_KM = 0.6


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
        stops = []
        for i, (address, truth) in enumerate(GEOCODE_CASES, start=1):
            result = geocoder.geocode_address(address)
            if result is None:
                failures.append(f"geocoding: '{address}' was not found")
                continue
            km = haversine_km(result, truth)
            self.stdout.write(f"geocode {address!r}: {result[0]:.5f},{result[1]:.5f} ({km * 1000:.0f} m from truth)")
            if km > GEOCODE_TOLERANCE_KM:
                failures.append(f"geocoding: '{address}' landed {km:.1f} km from its real spot {truth}")
            if result == geocoder._mock_geocode(address):
                failures.append(f"geocoding: '{address}' equals the mock coordinates (mock in use?)")
            if i <= 4:  # the zip variant repeats a location, keep the stop list distinct
                stops.append(SimpleNamespace(id=i, lat=result[0], lng=result[1]))
            time.sleep(0.2)
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
