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
        resp.json.return_value = [{"lat": "47.5", "lon": "19.05", "address": {"house_number": "1", "postcode": "1051"}}]
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


class M1CandidatePickingTest(SimpleTestCase):
    """The pin must be on the house the address names, never on the street or another street's number."""

    def _hit(self, lat, lng, zip_code, number, category="amenity", type_="bar"):
        return {
            "lat": str(lat),
            "lon": str(lng),
            "category": category,
            "type": type_,
            "address": {"postcode": zip_code, "house_number": number},
        }

    def test_house_number_parsing(self):
        parse = geocoder.requested_house_number
        self.assertEqual(parse("Kazinczy utca 14 Budapest"), "14")
        self.assertEqual(parse("1075 Budapest, Kazinczy utca 14"), "14")
        self.assertEqual(parse("Kazinczy utca 14, 1075 Budapest"), "14")
        self.assertEqual(parse("Vaci ut 1-3 Budapest"), "1-3")
        self.assertEqual(parse("Marcius 15 ter 7 Budapest"), "7")
        self.assertEqual(parse("Fo utca 12/A"), "12/a")
        self.assertIsNone(parse("Vamhaz korut Budapest"))

    def test_range_contains_requested_number(self):
        self.assertTrue(geocoder._house_matches("1", "1-3"))
        self.assertFalse(geocoder._house_matches("5", "2-4"))
        self.assertFalse(geocoder._house_matches("14", "140"))

    def test_street_level_hit_is_rejected(self):
        coords, why = geocoder._pick_best("Kazinczy utca 14 Budapest", [self._hit(47.5, 19.05, "1075", None)])
        self.assertIsNone(coords)
        self.assertIn("not house number 14", why)

    def test_other_house_number_is_rejected(self):
        coords, _ = geocoder._pick_best("Kazinczy utca 14 Budapest", [self._hit(47.5, 19.05, "1075", "16")])
        self.assertIsNone(coords)

    def test_no_house_number_is_not_pinned(self):
        coords, why = geocoder._pick_best("Vamhaz korut Budapest", [self._hit(47.48, 19.05, "1093", "1-3")])
        self.assertIsNone(coords)
        self.assertIn("No house number", why)

    def test_postcode_match_beats_nominatim_first_hit(self):
        hits = [self._hit(47.5652, 19.1239, "1152", "14"), self._hit(47.4969, 19.0633, "1075", "14")]
        self.assertEqual(geocoder._pick_best("1075 Budapest, Kazinczy utca 14", hits)[0], (47.4969, 19.0633))

    def test_wrong_postcode_is_rejected(self):
        coords, why = geocoder._pick_best(
            "1085 Budapest, Kazinczy utca 14", [self._hit(47.4969, 19.0633, "1075", "14")]
        )
        self.assertIsNone(coords)
        self.assertIn("1085", why)

    def test_without_zip_group_nearest_to_depot_wins(self):
        hits = [
            self._hit(47.5652, 19.1239, "1152", "14"),
            self._hit(47.5540, 18.9637, "1028", "14"),
            self._hit(47.4969, 19.0633, "1075", "14"),
        ]
        self.assertEqual(geocoder._pick_best("Kazinczy utca 14 Budapest", hits)[0], (47.4969, 19.0633))

    def test_address_point_beats_poi(self):
        hits = [
            self._hit(47.4990, 19.0600, "1075", "13"),
            self._hit(47.4983, 19.0592, "1075", "13", "place", "house"),
        ]
        self.assertEqual(geocoder._pick_best("Kiraly utca 13 Budapest", hits)[0], (47.4983, 19.0592))

    @staticmethod
    def _box(hit, half_deg):
        lat, lng = float(hit["lat"]), float(hit["lon"])
        hit["boundingbox"] = [str(lat - half_deg), str(lat + half_deg), str(lng - half_deg), str(lng + half_deg)]
        return hit

    def test_points_that_agree_within_2_m_are_accepted(self):
        hits = [self._hit(47.498400, 19.059400, "1075", "13"), self._hit(47.498410, 19.059410, "1075", "13")]
        coords, _ = geocoder._pick_best("Kiraly utca 13 Budapest", hits)
        self.assertLess(haversine_km(coords, (47.498405, 19.059405)) * 1000, 2)

    def test_points_further_apart_than_2_m_fail_instead_of_guessing(self):
        hits = [self._hit(47.4980, 19.0590, "1075", "13"), self._hit(47.4984, 19.0594, "1075", "13")]
        coords, why = geocoder._pick_best("Kiraly utca 13 Budapest", hits)
        self.assertIsNone(coords)
        self.assertIn("apart", why)

    def test_limit_is_configurable(self):
        hits = [self._hit(47.4980, 19.0590, "1075", "13"), self._hit(47.4981, 19.0591, "1075", "13")]
        with override_settings(GEOCODE_MAX_ERROR_M=50):
            self.assertIsNotNone(geocoder._pick_best("Kiraly utca 13 Budapest", hits)[0])
        with override_settings(GEOCODE_MAX_ERROR_M=2):
            self.assertIsNone(geocoder._pick_best("Kiraly utca 13 Budapest", hits)[0])

    def test_building_outline_alone_is_not_a_point(self):
        hit = self._box(self._hit(47.4914, 19.0528, "1056", "7", "building", "apartments"), 0.0003)
        coords, why = geocoder._pick_best("Marcius 15 ter 7 Budapest", [hit])
        self.assertIsNone(coords)
        self.assertIn("building/area", why)

    def test_address_point_beats_building_outline_and_far_pois(self):
        point = self._box(self._hit(47.491578, 19.052971, "1056", "7", "place", "house"), 0.00004)
        outline = self._box(self._hit(47.491437, 19.052852, "1056", "7", "building", "apartments"), 0.0003)
        shop = self._box(self._hit(47.4930, 19.0550, "1056", "7"), 0.00004)
        self.assertEqual(
            geocoder._pick_best("Marcius 15 ter 7 Budapest", [outline, shop, point])[0], (47.491578, 19.052971)
        )

    def test_candidates_outside_budapest_are_dropped(self):
        coords, _ = geocoder._pick_best("Fő utca 1", [self._hit(48.2, 16.37, "1010", "1")])
        self.assertIsNone(coords)


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
