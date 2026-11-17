import random
from collections import defaultdict

from django.test import SimpleTestCase

from .clustering import cluster_zip_atomic
from .testing.zip_fixtures import REALISTIC_DAY, ZIP_CENTROIDS, make_stops


def _assert_zip_atomic(test, clusters):
    seen = {}
    for i, cluster in enumerate(clusters):
        for stop in cluster:
            if stop.postal_code:
                test.assertEqual(seen.setdefault(stop.postal_code, i), i, f"zip {stop.postal_code} split")


class ZipAtomicTests(SimpleTestCase):
    def test_a2_ac1_ac2_property_over_random_seeds(self):
        zips = sorted(ZIP_CENTROIDS)
        for seed in range(60):
            rng = random.Random(seed)
            counts = {z: rng.randint(1, 30) for z in rng.sample(zips, rng.randint(1, len(zips)))}
            stops = make_stops(counts, seed=seed)
            k = rng.randint(1, 6)
            result = cluster_zip_atomic(stops, n_routes=k)
            _assert_zip_atomic(self, result.clusters)
            flat = [id(s) for c in result.clusters for s in c]
            self.assertEqual(len(flat), len(stops))  # AC2: nothing lost or duplicated
            self.assertEqual(set(flat), {id(s) for s in stops})
            self.assertLessEqual(sum(1 for c in result.clusters if c), k)  # AC3
            if len(counts) >= k:
                self.assertTrue(all(result.clusters), f"empty cluster, seed {seed}")

    def test_a2_ac4_balance_on_realistic_day(self):
        stops = make_stops(REALISTIC_DAY["zip_counts"])
        result = cluster_zip_atomic(stops, n_routes=len(REALISTIC_DAY["bikers"]))
        sizes = [len(c) for c in result.clusters]
        avg = len(stops) / len(sizes)
        largest_zip = max(REALISTIC_DAY["zip_counts"].values())
        # Allowed to exceed 1.5x avg only if a single zip forces it.
        self.assertLessEqual(max(sizes), max(1.5 * avg, largest_zip), sizes)
        self.assertLessEqual(max(sizes), 1.5 * avg, sizes)
        _assert_zip_atomic(self, result.clusters)

    def test_a2_ac4_single_big_zip_forces_imbalance(self):
        stops = make_stops({"1054": 60, "1051": 5, "1052": 5})
        result = cluster_zip_atomic(stops, n_routes=3)
        self.assertEqual(max(len(c) for c in result.clusters), 60)
        _assert_zip_atomic(self, result.clusters)

    def test_a2_ac5_oversized_zip_kept_whole_and_listed(self):
        stops = make_stops(REALISTIC_DAY["zip_counts"])
        result = cluster_zip_atomic(stops, n_routes=5, max_stops=48)
        self.assertEqual(result.oversized_zips, [{"zip": "1054", "stop_count": 56}])
        holders = [c for c in result.clusters if any(s.postal_code == "1054" for s in c)]
        self.assertEqual(len(holders), 1)
        self.assertEqual(sum(1 for s in holders[0] if s.postal_code == "1054"), 56)

    def test_a2_ac6_unzipped_bucketed_together(self):
        stops = make_stops({"1051": 10, "1052": 10, "1061": 10})
        loose = make_stops({"1081": 4}, seed=3)
        for s in loose:
            s.postal_code, s.raw_address = "", "somewhere"
        result = cluster_zip_atomic(stops + loose, n_routes=3)
        self.assertEqual({id(s) for s in result.unzipped_stops}, {id(s) for s in loose})
        holders = [c for c in result.clusters if any(s in c for s in loose)]
        self.assertEqual(len(holders), 1)
        self.assertTrue(all(s in holders[0] for s in loose))

    def test_a2_no_zips_at_all_falls_back_to_geographic_split(self):
        stops = make_stops({"1051": 6, "1096": 6})
        for s in stops:
            s.postal_code, s.raw_address = "", ""
        result = cluster_zip_atomic(stops, n_routes=2)
        self.assertEqual(sorted(len(c) for c in result.clusters), [6, 6])
        self.assertEqual(len(result.unzipped_stops), 12)

    def test_a2_ac7_deterministic(self):
        def run():
            stops = make_stops(REALISTIC_DAY["zip_counts"])
            res = cluster_zip_atomic(stops, n_routes=4)
            return [[s.name for s in c] for c in res.clusters]

        self.assertEqual(run(), run())

    def test_a2_targets_are_index_aligned(self):
        stops = make_stops({"1051": 20, "1052": 10, "1061": 10})
        result = cluster_zip_atomic(stops, targets=[10, 30, 0])
        self.assertEqual([len(c) for c in result.clusters], [10, 30, 0])
        self.assertEqual(sum(len(c) for c in result.clusters), len(stops))  # nothing dropped

    def test_a2_edge_cases(self):
        self.assertEqual(cluster_zip_atomic([], n_routes=3).clusters, [[], [], []])
        stops = make_stops({"1051": 3})
        self.assertEqual([len(c) for c in cluster_zip_atomic(stops, n_routes=1).clusters], [3])
        # more routes than zips: extra routes stay empty, zip not split
        result = cluster_zip_atomic(stops, n_routes=4)
        self.assertEqual(sorted(len(c) for c in result.clusters), [0, 0, 0, 3])
        with self.assertRaises(ValueError):
            cluster_zip_atomic(stops, targets=[])

    def test_a2_groups_by_zip_only(self):
        stops = make_stops({"1051": 7, "1052": 7, "1053": 7, "1054": 7})
        result = cluster_zip_atomic(stops, n_routes=2)
        per_route = [defaultdict(int) for _ in result.clusters]
        for i, c in enumerate(result.clusters):
            for s in c:
                per_route[i][s.postal_code] += 1
        for counts in per_route:
            self.assertTrue(all(v == 7 for v in counts.values()))
