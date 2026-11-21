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

# (address as typed in the daily files - with postal code, (lat, lng) of the house from OpenStreetMap).
# A pinned address must be on its house (250 m) and never an offline-mock coordinate.
GEOCODE_CASES = [
    ("1075 Budapest, Kazinczy utca 14", (47.49693, 19.06331)),
    ("1085 Budapest, Gyulai Pál utca 2", (47.49527, 19.06784)),
    ("1075 Budapest, Károly körút 3", (47.49539, 19.05948)),
    ("1056 Budapest, Március 15. tér 7", (47.49158, 19.05297)),
    ("1082 Budapest, Futó utca 37", (47.48623, 19.07413)),
]
# The same houses as the planner's files really look: birth dates, phones, notes, abbreviations, missing accents.
# They go through the whole address pipeline (parser included); each must be found on its house.
MESSY_CASES = [
    ("Kazinczy u. 14 1075 Bp. szül. 1990.05.12", (47.49693, 19.06331)),
    ("Dr. Kovács Béla, 1085 Budapest, Gyulai Pal u. 2, tel: +36 20 123 4567", (47.49527, 19.06784)),
    ("1075 Budapest, Károly krt. 3 kapukód: 1234", (47.49539, 19.05948)),
    ("Március 15. tér 7 1056 Budapest 1985.03.07", (47.49158, 19.05297)),
    ("1082 Budapest Futó u 37 2. em. 5. ajtó", (47.48623, 19.07413)),
]
MESSY_MIN_RESOLVED = 4  # of 5 must resolve without a human
GEOCODE_TOLERANCE_KM = 0.25  # same street: Nominatim may return any OSM object carrying the house number


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
        self._pipeline(failures)
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
            self.stdout.write(
                f"geocode {address!r}: {result[0]:.5f},{result[1]:.5f} ({km * 1000:.0f} m from the house)"
            )
            if km > GEOCODE_TOLERANCE_KM:
                failures.append(f"geocoding: '{address}' landed {km * 1000:.0f} m from its house {truth}")
            if result == geocoder._mock_geocode(address):
                failures.append(f"geocoding: '{address}' equals the mock coordinates (mock in use?)")
            stops.append(SimpleNamespace(id=i, lat=result[0], lng=result[1]))
        return stops

    def _pipeline(self, failures):
        """Per-stage resolve rate of the address pipeline (cache/raw/parsed/google/manual) on messy real addresses."""
        from planner.geocode_pipeline import run
        from planner.models import DeliverySession, DeliveryStop

        session = DeliverySession.objects.create(name="smoke-address-pipeline")
        try:
            stops = [
                DeliveryStop.objects.create(session=session, name=f"smoke {i}", raw_address=raw)
                for i, (raw, _) in enumerate(MESSY_CASES, start=1)
            ]
            truth = {s.id: t for s, (_, t) in zip(stops, MESSY_CASES, strict=True)}
            done = list(run(stops))
        finally:
            session.delete()
        by_stage: dict[str, int] = {}
        resolved = 0
        for stop in done:
            by_stage[stop.geocode_stage] = by_stage.get(stop.geocode_stage, 0) + 1
            if stop.geocode_status != "success":
                self.stdout.write(f"pipeline {stop.raw_address!r}: NOT resolved ({stop.geocode_error})")
                continue
            resolved += 1
            km = haversine_km((stop.lat, stop.lng), truth[stop.id])
            self.stdout.write(
                f"pipeline {stop.raw_address!r} -> {stop.cleaned_address or stop.raw_address!r} "
                f"[{stop.geocode_stage}] {km * 1000:.0f} m from the house"
            )
            if km > GEOCODE_TOLERANCE_KM:
                failures.append(f"pipeline: '{stop.raw_address}' landed {km * 1000:.0f} m from its house")
        self.stdout.write(
            f"pipeline resolve rate: {resolved}/{len(MESSY_CASES)} without a human; by stage {dict(sorted(by_stage.items()))}"
        )
        if resolved < MESSY_MIN_RESOLVED:
            failures.append(
                f"pipeline: only {resolved}/{len(MESSY_CASES)} messy addresses resolved (need {MESSY_MIN_RESOLVED})"
            )

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
