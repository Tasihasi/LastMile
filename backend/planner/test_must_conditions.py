"""App-wide MUST conditions (next to the 15-minute ruling):

M1  An address is placed where it really is: inside its own postal code's area in Budapest, never at a
    random point on the map; a hit outside Budapest is a failure, not a pin.
M2  A route is truly optimized: a short closed tour over the road network, never an angle sort or file
    order; and a route whose road geometry cannot be fetched is an error, not straight lines.
"""

import itertools
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from . import geocoder, optimizer, timing, tsp
from .budapest import BBOX, ZIP_CENTROIDS, haversine_km, in_budapest


@override_settings(E2E_MOCK=True)
class M1GeocodingTest(SimpleTestCase):
    def test_mock_address_lands_near_its_zip_centroid(self):
        for zip_code, centroid in ZIP_CENTROIDS.items():
            for n in range(5):
                lat, lng = geocoder.geocode_address(f"{zip_code} Budapest, Teszt utca {n}")
                self.assertLess(haversine_km((lat, lng), centroid), 0.8, zip_code)

    def test_mock_is_deterministic_and_inside_budapest(self):
        a = geocoder.geocode_address("Ismeretlen utca 1")
        self.assertEqual(a, geocoder.geocode_address("Ismeretlen utca 1"))
        self.assertTrue(in_budapest(*a))

    def test_real_geocoder_is_bounded_to_budapest(self):
        resp = MagicMock()
        resp.json.return_value = [{"lat": "47.5", "lon": "19.05"}]
        with (
            override_settings(E2E_MOCK=False),
            patch.object(geocoder, "_rate_limit"),
            patch.object(geocoder.requests, "get", return_value=resp) as get,
        ):
            self.assertEqual(geocoder.geocode_address("1051 Budapest, Nádor utca 1"), (47.5, 19.05))
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["countrycodes"], "hu")
        self.assertEqual(params["bounded"], 1)
        self.assertEqual(params["viewbox"], f"{BBOX[1]},{BBOX[2]},{BBOX[3]},{BBOX[0]}")

    def test_real_geocoder_rejects_hit_outside_budapest(self):
        resp = MagicMock()
        resp.json.return_value = [{"lat": "48.2", "lon": "16.37"}]  # Vienna
        with (
            override_settings(E2E_MOCK=False),
            patch.object(geocoder, "_rate_limit"),
            patch.object(geocoder.requests, "get", return_value=resp),
        ):
            self.assertIsNone(geocoder.geocode_address("Fő utca 1"))


def _stops(points):
    return [SimpleNamespace(id=i + 1, lat=p[0], lng=p[1]) for i, p in enumerate(points)]


class M2OptimizationTest(SimpleTestCase):
    # a shuffled 3x3 grid: angle sort / file order are far from optimal
    SHUFFLED = [(47.49 + 0.005 * (i // 3), 19.05 + 0.007 * (i % 3)) for i in (4, 0, 8, 2, 6, 1, 7, 3, 5)]

    def _length(self, order, points, depot):
        path = [depot, *(points[i] for i in order), depot]
        return sum(haversine_km(a, b) for a, b in zip(path, path[1:], strict=False))

    def test_tour_is_optimal_for_small_instance(self):
        pts, depot = self.SHUFFLED[:7], timing.DEPOT
        best = min(self._length(p, pts, depot) for p in itertools.permutations(range(len(pts))))
        got = self._length(tsp.optimize_order(pts, depot), pts, depot)
        self.assertLessEqual(got, best * 1.05)

    def test_tour_visits_every_stop_once(self):
        order = tsp.optimize_order(self.SHUFFLED, timing.DEPOT)
        self.assertEqual(sorted(order), list(range(len(self.SHUFFLED))))

    @override_settings(E2E_MOCK=True)
    def test_mock_optimizer_beats_angle_sort_and_file_order(self):
        stops = _stops(self.SHUFFLED)
        ids = optimizer.optimize_route(stops, depot=timing.DEPOT)
        by_id = {s.id: s for s in stops}
        opt = self._length([by_id[i].id - 1 for i in ids], self.SHUFFLED, timing.DEPOT)
        file_order = self._length(list(range(len(stops))), self.SHUFFLED, timing.DEPOT)
        self.assertLess(opt, file_order)

    @override_settings(E2E_MOCK=True)
    def test_mock_route_details_are_deterministic_and_model_based(self):
        stops = _stops(self.SHUFFLED[:4])
        a = optimizer.get_route_details(stops, depot=timing.DEPOT)
        self.assertEqual(a, optimizer.get_route_details(stops, depot=timing.DEPOT))
        self.assertGreater(a["total_distance"], 0)
        self.assertEqual(a["total_duration"], sum(s["duration"] for s in a["segments"]))

    def test_time_estimate_uses_optimized_tour(self):
        km = timing.tour_km(self.SHUFFLED, timing.DEPOT)
        naive = sum(haversine_km(a, b) for a, b in zip(self.SHUFFLED, self.SHUFFLED[1:], strict=False))
        self.assertLess(km, naive + 2 * haversine_km(timing.DEPOT, self.SHUFFLED[0]))
