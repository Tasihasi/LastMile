"""A2: the cluster endpoint never splits a postal code across routes."""

from django.test import TestCase

from .models import DeliverySession, DeliveryStop
from .tests import _make_biker, _make_planner


class SplitZipAtomicAPITest(TestCase):
    def setUp(self):
        self.planner, self.planner_client = _make_planner("a2_planner")
        self.biker_a, _ = _make_biker("a2_biker_a")
        self.biker_b, _ = _make_biker("a2_biker_b")
        self.session = DeliverySession.objects.create(name="A2 day", status="not_started")

    def _stops(self, zip_counts, zipless=0):
        stops = []
        n = 0
        for zip_code, count in zip_counts.items():
            for _ in range(count):
                n += 1
                stops.append(
                    DeliveryStop(
                        session=self.session,
                        name=f"S{n}",
                        raw_address=f"{zip_code} Budapest, Utca {n}",
                        postal_code=zip_code,
                        lat=47.49 + n * 0.0007,
                        lng=19.05 + (n % 7) * 0.003,
                        geocode_status="success",
                    )
                )
        for _ in range(zipless):
            n += 1
            stops.append(
                DeliveryStop(
                    session=self.session,
                    name=f"S{n}",
                    raw_address="Valami utca",
                    lat=47.5,
                    lng=19.06,
                    geocode_status="success",
                )
            )
        DeliveryStop.objects.bulk_create(stops)

    def _assert_no_zip_split(self, resp):
        by_zip = {}
        for route in resp.json()["sub_routes"]:
            child = DeliverySession.objects.get(id=route["id"])
            for z in child.stops.values_list("postal_code", flat=True):
                by_zip.setdefault(z, set()).add(route["id"])
        for z, routes in by_zip.items():
            self.assertEqual(len(routes), 1, f"zip {z} split")

    def _cluster(self, payload):
        return self.planner_client.post(f"/api/sessions/{self.session.id}/cluster/", payload, format="json")

    def test_a2_default_split_never_splits_a_zip(self):
        self._stops({"1051": 12, "1052": 9, "1061": 15, "1072": 6, "1081": 11})
        resp = self._cluster({"n_routes": 3})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["oversized_zips"], [])
        self.assertEqual(resp.json()["unzipped_stop_ids"], [])
        self._assert_no_zip_split(resp)

    def test_a2_ac5_oversized_zip_reported_via_api(self):
        self._stops({"1054": 20, "1051": 3})
        resp = self._cluster({"n_routes": 2, "max_stops_per_route": 10})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["oversized_zips"], [{"zip": "1054", "stop_count": 20}])

    def test_a2_ac6_zipless_stops_listed_and_request_ok(self):
        self._stops({"1051": 8, "1061": 8}, zipless=3)
        resp = self._cluster({"n_routes": 2})
        self.assertEqual(resp.status_code, 201)
        ids = resp.json()["unzipped_stop_ids"]
        self.assertEqual(len(ids), 3)
        addresses = set(DeliveryStop.objects.filter(id__in=ids).values_list("raw_address", flat=True))
        self.assertEqual(addresses, {"Valami utca"})

    def test_a2_ac8_assignments_zip_lock_still_atomic(self):
        self._stops({"1051": 10, "1052": 8, "1061": 7, "1072": 9})
        resp = self._cluster(
            {
                "assignments": [
                    {"biker_id": self.biker_a.id, "target_stops": 20, "district": None, "zip": None},
                    {"biker_id": self.biker_b.id, "target_stops": 8, "district": None, "zip": 1052},
                ]
            }
        )
        self.assertEqual(resp.status_code, 201)
        self._assert_no_zip_split(resp)
        locked = next(r for r in resp.json()["sub_routes"] if r["owner_id"] == self.biker_b.id)
        self.assertEqual(locked["stop_count"], 8)

    def test_a2_ac8_district_lock_with_two_bikers_keeps_zips_whole(self):
        self._stops({"1051": 10, "1052": 8, "1055": 6, "1072": 12})
        resp = self._cluster(
            {
                "assignments": [
                    {"biker_id": self.biker_a.id, "target_stops": 12, "district": 5, "zip": None},
                    {"biker_id": self.biker_b.id, "target_stops": 12, "district": 5, "zip": None},
                    {"biker_id": None, "target_stops": 12, "district": None, "zip": None},
                ]
            }
        )
        self.assertEqual(resp.status_code, 201)
        self._assert_no_zip_split(resp)

    def test_a2_ac8_two_bikers_locked_to_same_zip_does_not_split_it(self):
        self._stops({"1051": 10, "1052": 8})
        resp = self._cluster(
            {
                "assignments": [
                    {"biker_id": self.biker_a.id, "target_stops": 5, "district": None, "zip": 1051},
                    {"biker_id": self.biker_b.id, "target_stops": 5, "district": None, "zip": 1051},
                    {"biker_id": None, "target_stops": 8, "district": None, "zip": None},
                ]
            }
        )
        self.assertEqual(resp.status_code, 201)
        self._assert_no_zip_split(resp)

    def test_a2_biker_cannot_cluster(self):
        self._stops({"1051": 3, "1052": 3})
        _, biker_client = _make_biker("a2_other_biker")
        resp = biker_client.post(f"/api/sessions/{self.session.id}/cluster/", {"n_routes": 2}, format="json")
        self.assertEqual(resp.status_code, 403)
