import re

from django.contrib.auth.models import User
from django.test import TestCase

from .testing.zip_fixtures import REALISTIC_DAY, ZIP_CENTROIDS, make_session, make_stops


def _snapshot(stops):
    return [(s.name, s.postal_code, s.lat, s.lng) for s in stops]


class ZipFixturesTests(TestCase):
    def test_a0_ac1_deterministic_same_seed(self):
        a = make_stops(REALISTIC_DAY["zip_counts"], seed=7)
        b = make_stops(REALISTIC_DAY["zip_counts"], seed=7)
        self.assertEqual(_snapshot(a), _snapshot(b))

    def test_a0_ac1_different_seed_differs(self):
        a = make_stops({"1051": 5}, seed=1)
        b = make_stops({"1051": 5}, seed=2)
        self.assertNotEqual(_snapshot(a), _snapshot(b))

    def test_a0_ac2_realistic_day_has_zip_over_route_capacity(self):
        counts = REALISTIC_DAY["zip_counts"]
        self.assertGreater(max(counts.values()), 48)
        self.assertEqual(len(counts), 34)
        self.assertTrue(150 <= sum(counts.values()) <= 250)
        self.assertTrue(3 <= len(REALISTIC_DAY["bikers"]) <= 5)
        self.assertEqual(len(make_stops(counts)), sum(counts.values()))

    def test_a0_ac3_postal_codes_and_bbox(self):
        for stop in make_stops(REALISTIC_DAY["zip_counts"]):
            self.assertRegex(stop.postal_code, r"^1\d{3}$")
            self.assertTrue(47.35 <= stop.lat <= 47.60, stop.lat)
            self.assertTrue(18.95 <= stop.lng <= 19.20, stop.lng)

    def test_a0_ac3_centroids_all_valid(self):
        for postal_code in ZIP_CENTROIDS:
            self.assertTrue(re.match(r"^1\d{3}$", postal_code))

    def test_a0_fixture_zips_are_districts_v_to_ix(self):
        zips = set(REALISTIC_DAY["zip_counts"]) | set(ZIP_CENTROIDS)
        self.assertEqual(len(zips), 34)
        for z in zips:
            self.assertRegex(z, r"^10[5-9]\d$")

    def test_a0_empty_input(self):
        self.assertEqual(make_stops({}), [])


class MakeSessionTests(TestCase):
    def test_a0_make_session_persists_stops(self):
        owner = User.objects.create_user("fixture_owner")
        session = make_session(owner, {"1051": 3, "1054": 2})
        self.assertEqual(session.stops.count(), 5)
        self.assertEqual(session.stops.filter(postal_code="1054").count(), 2)
