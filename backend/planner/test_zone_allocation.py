"""A5: zone-first, time-capacity-aware allocation."""

import time
from types import SimpleNamespace

from django.test import TestCase

from . import timing, zones
from .models import DeliverySession, DeliveryStop
from .testing.zip_fixtures import REALISTIC_DAY, make_stops
from .tests import _make_biker, _make_planner
from .zone_allocation import allocate_zones, zone_units

DAY = REALISTIC_DAY["zip_counts"]


def stub_estimator(stops, multiplier, depot):
    """1 minute per stop x multiplier: no geography, so capacity maths is easy to reason about."""
    return len(stops) * multiplier


def spread_estimator(stops, multiplier, depot):
    """Stop count plus a penalty for geographic spread, so detours cost time."""
    if not stops:
        return 0.0
    lats = [s.lat for s in stops]
    return len(stops) * multiplier + 100 * (max(lats) - min(lats))


def _zone_of(stop):
    return zones.zone_for_zip(stop.postal_code) or f"zip:{stop.postal_code}"


class AllocateZonesTests(TestCase):
    def _bikers(self, n, window, multiplier=1.0):
        return [{"id": i, "window_minutes": window, "multiplier": multiplier} for i in range(n)]

    def test_ac1_ac2_zones_whole_and_within_capacity(self):
        stops = make_stops(DAY)
        res = allocate_zones(stops, self._bikers(4, 220))
        units = zone_units(stops)
        seen = {}
        for bid, route in res["routes"].items():
            for z in route["zones"]:
                self.assertNotIn(z, seen, f"zone {z} on two routes")
                seen[z] = bid
            self.assertLessEqual(route["load_minutes"], route["capacity_minutes"])
        for z, bid in seen.items():
            on_route = sum(1 for s in res["routes"][bid]["stops"] if _zone_of(s) == z)
            self.assertEqual(on_route, len(units[z]))
            for other, route in res["routes"].items():
                if other != bid:
                    self.assertFalse(any(_zone_of(s) == z for s in route["stops"]))

    def test_ac3_unplaceable_zone_is_reported_not_forced(self):
        stops = make_stops({"1051": 30, "1061": 5})
        res = allocate_zones(stops, self._bikers(2, 10), estimator=stub_estimator)
        names = [u["zone"] for u in res["unassigned_zones"]]
        self.assertEqual(names, [zones.zone_for_zip("1051")])
        self.assertEqual(res["unassigned_zones"][0]["stop_count"], 30)
        placed = sum(len(r["stops"]) for r in res["routes"].values())
        self.assertEqual(placed, 5)

    def test_ac4_realistic_day_utilisation_and_tight_params(self):
        stops = make_stops(DAY)
        ok = allocate_zones(stops, self._bikers(4, 220))
        self.assertEqual(ok["unassigned_zones"], [])
        load = sum(r["load_minutes"] for r in ok["routes"].values())
        cap = sum(r["capacity_minutes"] for r in ok["routes"].values())
        self.assertGreaterEqual(load / cap, 0.85)
        tight = allocate_zones(stops, self._bikers(4, 120))
        self.assertTrue(tight["unassigned_zones"])

    def test_ac5_far_apart_clusters_stay_together(self):
        north = make_stops({"1051": 5, "1052": 5, "1053": 5})
        south = make_stops({"1081": 5, "1082": 5, "1083": 5}, seed=7)
        for s in south:
            s.lat -= 0.2  # far away from the first cluster
        res = allocate_zones(north + south, self._bikers(2, 40), estimator=spread_estimator)
        for route in res["routes"].values():
            self.assertTrue(route["stops"])
            self.assertEqual(len({s.lat > 47.3 for s in route["stops"]}), 1, "route mixes the two areas")

    def test_ac6_deterministic_and_fast(self):
        stops = make_stops(DAY)
        bikers = self._bikers(6, 150)
        t = time.perf_counter()
        a = allocate_zones(stops, bikers)
        self.assertLess(time.perf_counter() - t, 2.0)
        b = allocate_zones(stops, bikers)
        self.assertEqual(a["assignments"], b["assignments"])
        self.assertGreaterEqual(len(stops), 200)

    def test_ac7_slower_biker_gets_fewer_stops(self):
        stops = make_stops({"1051": 8, "1061": 8, "1071": 8, "1081": 8, "1092": 8})
        bikers = [
            {"id": "fast", "window_minutes": 40, "multiplier": 1.0},
            {"id": "slow", "window_minutes": 40, "multiplier": 2.0},
        ]
        res = allocate_zones(stops, bikers, estimator=stub_estimator)
        self.assertGreater(len(res["routes"]["fast"]["stops"]), len(res["routes"]["slow"]["stops"]))

    def test_unzoned_zip_is_own_unit_and_zipless_stops_are_skipped(self):
        stops = make_stops({"1051": 3, "1052": 3})
        for s in stops[:3]:
            s.postal_code = "1111"  # outside the zone config
        loose = make_stops({"1051": 2}, seed=3)
        for s in loose:
            s.postal_code, s.raw_address = "", ""
        units = zone_units(stops + loose)
        self.assertIn("zip:1111", units)
        self.assertEqual(sum(len(v) for v in units.values()), 6)

    def test_empty_inputs(self):
        self.assertEqual(allocate_zones([], self._bikers(2, 60))["unassigned_zones"], [])

    def test_f4_routes_are_packed_to_the_window_not_the_overrun(self):
        res = allocate_zones(make_stops(DAY), self._bikers(4, 220))
        for route in res["routes"].values():
            self.assertLessEqual(route["load_minutes"], 220)
        # 200 min only fits Z04 (213 min) by borrowing the overrun: it must be reported, not packed.
        tight = allocate_zones(make_stops(DAY), self._bikers(4, 200))
        self.assertTrue(tight["unassigned_zones"])


class TimingTests(TestCase):
    def test_estimate_scales_with_multiplier_and_prefers_given_travel(self):
        stops = [SimpleNamespace(lat=47.5, lng=19.05), SimpleNamespace(lat=47.51, lng=19.06)]
        base = timing.estimate_route_minutes(stops, travel_minutes=10)
        self.assertEqual(base, 2 * timing.SERVICE_TIME_PER_STOP_MIN + 10 + timing.BREAK_MIN)
        slower = timing.estimate_route_minutes(stops, multiplier=2, travel_minutes=10)
        self.assertEqual(slower - base, 2 * timing.SERVICE_TIME_PER_STOP_MIN)
        self.assertEqual(timing.estimate_route_minutes([]), 0)


class ZoneFirstAPITest(TestCase):
    def setUp(self):
        self.planner, self.client_ = _make_planner("a5_planner")
        self.bikers = [_make_biker(f"a5_biker_{i}")[0] for i in range(4)]
        self.session = DeliverySession.objects.create(name="A5 day", status="not_started")
        stops = make_stops(DAY)
        for s in stops:
            s.session = self.session
        DeliveryStop.objects.bulk_create(stops)

    def _split(self, window, **extra):
        payload = {
            "assignments": [
                {"biker_id": b.id, "target_stops": 0, "window_minutes": window, **extra} for b in self.bikers
            ]
        }
        return self.client_.post(f"/api/sessions/{self.session.id}/cluster/", payload, format="json")

    def test_ac4_end_to_end_feasible(self):
        resp = self._split(220)
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["unassigned_zones"], [])
        total = 0
        for r in body["sub_routes"]:
            self.assertLessEqual(r["load_minutes"], r["capacity_minutes"])
            self.assertTrue(r["zones"])
            total += r["stop_count"]
        self.assertEqual(total, sum(DAY.values()))
        self.assertEqual(body["zip_conflicts"], [])

    def test_ac3_tight_windows_report_unassigned_but_lose_no_stops(self):
        body = self._split(120).json()
        self.assertTrue(body["unassigned_zones"])
        self.assertEqual(sum(r["stop_count"] for r in body["sub_routes"]), sum(DAY.values()))
        self.assertEqual(body["zip_conflicts"], [])

    def test_without_windows_behaves_like_before(self):
        payload = {"assignments": [{"biker_id": b.id, "target_stops": 60} for b in self.bikers]}
        resp = self.client_.post(f"/api/sessions/{self.session.id}/cluster/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["unassigned_zones"], [])
        self.assertNotIn("load_minutes", resp.json()["sub_routes"][0])

    def test_invalid_window_is_400(self):
        self.assertEqual(self._split(-5).status_code, 400)
        self.assertEqual(self._split("abc").status_code, 400)
        self.assertEqual(self._split(220, multiplier=0).status_code, 400)

    def test_f2_mixed_window_payloads_are_rejected(self):
        mixed = {
            "assignments": [
                {"biker_id": self.bikers[0].id, "target_stops": 0, "window_minutes": 200},
                {"biker_id": self.bikers[1].id, "target_stops": 50},
            ]
        }
        resp = self.client_.post(f"/api/sessions/{self.session.id}/cluster/", mixed, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("every biker or for none", resp.json()["error"])
        locked = {
            "assignments": [
                {"biker_id": b.id, "target_stops": 0, "window_minutes": 200, "district": 8} for b in self.bikers
            ]
        }
        resp = self.client_.post(f"/api/sessions/{self.session.id}/cluster/", locked, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(DeliverySession.objects.filter(parent=self.session).exists())

    def test_f3_bikers_the_windows_do_not_need_get_no_empty_route(self):
        body = self._split(420).json()
        self.assertTrue(body["unused_bikers"])
        counts = [r["stop_count"] for r in body["sub_routes"]]
        self.assertTrue(all(c > 0 for c in counts))
        self.assertEqual(len(body["sub_routes"]) + len(body["unused_bikers"]), len(self.bikers))
        self.assertEqual(sum(counts), sum(DAY.values()))
