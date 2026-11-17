"""A6: minimal zone-splitting fallback."""

import itertools
import random
from collections import defaultdict

from django.test import SimpleTestCase, TestCase

from . import zones
from .clustering import find_zip_conflicts, stop_zip
from .models import DeliverySession, DeliveryStop
from .testing.zip_fixtures import REALISTIC_DAY, make_stops
from .tests import _make_biker, _make_planner
from .zone_allocation import allocate_zones
from .zone_splitting import resolve_unassigned


def stub(stops, multiplier, depot):
    return len(stops) * multiplier


def run(stops, windows):
    bikers = [{"id": i, "window_minutes": w} for i, w in enumerate(windows)]
    alloc = allocate_zones(stops, bikers, estimator=stub, tolerance=0)
    res = resolve_unassigned(alloc, bikers, estimator=stub, tolerance=0)
    return alloc, res


def zip_routes(res):
    out = defaultdict(set)
    for bid, route in res["routes"].items():
        for s in route["stops"]:
            out[stop_zip(s)].add(bid)
    return out


class ResolveUnassignedTests(SimpleTestCase):
    def test_ac3_one_zone_must_break(self):
        stops = make_stops({"1082": 6, "1083": 6})  # both in zone Z12: 12 stops, windows of 10
        alloc, res = run(stops, [10, 10])
        self.assertEqual(len(alloc["unassigned_zones"]), 1)
        self.assertEqual([z["zone_id"] for z in res["split_zones"]], [zones.zone_for_zip("1082")])
        parts = res["split_zones"][0]["parts"]
        self.assertEqual(sorted(z for p in parts for z in p["zips"]), ["1082", "1083"])
        self.assertEqual(res["over_capacity_routes"], [])

    def test_ac3_solvable_without_breaking(self):
        stops = make_stops({"1082": 6, "1083": 6})
        _, res = run(stops, [12, 12])
        self.assertEqual(res["split_zones"], [])

    def test_ac1_ac2_every_stop_once_and_zips_whole(self):
        stops = make_stops(REALISTIC_DAY["zip_counts"])
        _, res = run(stops, [60, 60, 60, 60])
        placed = [id(s) for r in res["routes"].values() for s in r["stops"]]
        self.assertEqual(len(placed), len(set(placed)))
        # stops of zones step 1 placed + resolved ones: nothing but unzipped may be missing
        self.assertEqual(set(placed), {id(s) for s in stops if stop_zip(s)})
        for z, routes in zip_routes(res).items():
            self.assertEqual(len(routes), 1, f"zip {z} split")

    def test_ac4_oversize_zip_is_flagged_and_other_routes_stay_within_capacity(self):
        stops = make_stops({"1054": 20, "1061": 4, "1071": 4})
        _, res = run(stops, [10, 10, 10])
        self.assertIn("1054", res["over_capacity_zips"])
        self.assertEqual(len(res["over_capacity_routes"]), 1)
        for bid, route in res["routes"].items():
            if bid not in res["over_capacity_routes"]:
                self.assertLessEqual(route["load_minutes"], route["capacity_minutes"])
        self.assertEqual(len(zip_routes(res)["1054"]), 1)

    def test_ac5_matches_brute_force_minimum(self):
        zone_zips = [z for z in ("1051", "1052", "1053", "1056", "1054", "1055", "1061", "1065") if z]
        checked = 0
        for seed in range(400):
            rng = random.Random(seed)
            picked = rng.sample(zone_zips, rng.randint(4, 6))
            counts = {z: rng.randint(3, 7) for z in picked}
            stops = make_stops(counts, seed=seed)
            k = rng.randint(2, 3)
            windows = [-(-sum(counts.values()) // k) + rng.randint(0, 4) for _ in range(k)]
            alloc, res = run(stops, windows)
            unit = alloc["unassigned_stops"]
            if not unit or res["over_capacity_routes"]:
                continue
            zl = sorted({(zn, stop_zip(s)) for zn, ss in unit.items() for s in ss})
            sizes = {
                k: sum(
                    1
                    for ss in unit.values()
                    for s in ss
                    if (zones.zone_for_zip(stop_zip(s)) or f"zip:{stop_zip(s)}", stop_zip(s)) == k
                )
                for k in zl
            }
            base = [len(alloc["routes"][i]["stops"]) for i in range(len(windows))]
            best = None
            for plan in itertools.product(range(len(windows)), repeat=len(zl)):
                loads = list(base)
                for k, r in zip(zl, plan, strict=True):
                    loads[r] += sizes[k]
                if any(loads[i] > windows[i] for i in range(len(windows))):
                    continue
                by_zone = defaultdict(set)
                for k, r in zip(zl, plan, strict=True):
                    by_zone[k[0]].add(r)
                broken = sum(1 for v in by_zone.values() if len(v) > 1)
                best = broken if best is None else min(best, broken)
            if best is not None:
                self.assertEqual(len(res["split_zones"]), best, f"seed {seed}")
                checked += 1
        self.assertGreater(checked, 10)

    def test_nothing_unassigned_is_a_noop(self):
        stops = make_stops({"1051": 3})
        _, res = run(stops, [50])
        self.assertEqual(res["split_zones"], [])
        self.assertEqual(res["over_capacity_zips"], [])


class SplitZonesAPITest(TestCase):
    def setUp(self):
        _, self.client_ = _make_planner("a6_planner")
        self.bikers = [_make_biker(f"a6_biker_{i}")[0] for i in range(4)]
        self.session = DeliverySession.objects.create(name="A6 day", status="not_started")
        stops = make_stops(REALISTIC_DAY["zip_counts"])
        for s in stops:
            s.session = self.session
        DeliveryStop.objects.bulk_create(stops)

    def _split(self, window):
        payload = {
            "assignments": [{"biker_id": b.id, "target_stops": 0, "window_minutes": window} for b in self.bikers]
        }
        return self.client_.post(f"/api/sessions/{self.session.id}/cluster/", payload, format="json")

    def test_tight_windows_report_split_zones_with_route_names(self):
        resp = self._split(150)
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        names = {r["name"] for r in body["sub_routes"]}
        self.assertTrue(body["unassigned_zones"])
        self.assertTrue(body["split_zones"])
        for z in body["split_zones"]:
            self.assertGreater(len(z["parts"]), 1)
            for p in z["parts"]:
                self.assertIn(p["route"], names)
        self.assertEqual(sum(r["stop_count"] for r in body["sub_routes"]), sum(REALISTIC_DAY["zip_counts"].values()))
        self.assertEqual(body["zip_conflicts"], [])
        children = list(DeliverySession.objects.filter(parent=self.session))
        self.assertEqual(find_zip_conflicts(children), [])

    def test_feasible_windows_split_nothing(self):
        body = self._split(200).json()
        self.assertEqual(body["split_zones"], [])
        self.assertEqual(body["over_capacity_zips"], [])
        self.assertFalse(any(r["over_capacity"] for r in body["sub_routes"]))

    def test_over_capacity_route_is_flagged(self):
        body = self._split(40).json()
        self.assertTrue(any(r["over_capacity"] for r in body["sub_routes"]))
        self.assertTrue(body["over_capacity_zips"])
        self.assertEqual(sum(r["stop_count"] for r in body["sub_routes"]), sum(REALISTIC_DAY["zip_counts"].values()))


class SplitZonesOnSessionTest(TestCase):
    def test_session_json_lists_split_zones_from_current_state(self):
        _, client = _make_planner("a6_view_planner")
        parent = DeliverySession.objects.create(name="P", status="split")
        a = DeliverySession.objects.create(name="P_1", parent=parent)
        b = DeliverySession.objects.create(name="P_2", parent=parent)
        for sess, z in ((a, "1082"), (b, "1083"), (a, "1051")):
            DeliveryStop.objects.create(
                session=sess, name="s", raw_address=z, postal_code=z, lat=47.5, lng=19.0, geocode_status="success"
            )
        body = client.get(f"/api/sessions/{parent.id}/").json()
        self.assertEqual(
            body["split_zones"],
            [
                {
                    "zone_id": zones.zone_for_zip("1082"),
                    "parts": [{"zips": ["1082"], "route": "P_1"}, {"zips": ["1083"], "route": "P_2"}],
                }
            ],
        )
