"""A3: find_zip_conflicts and the zip_conflicts field on API responses."""

from django.test import TestCase, override_settings

from . import zones
from .clustering import find_zip_conflicts
from .models import DeliverySession, DeliveryStop
from .tests import _make_biker, _make_planner


def _route(parent, name, zip_counts, **stop_kwargs):
    child = DeliverySession.objects.create(parent=parent, name=name)
    n = 0
    for zip_code, count in zip_counts.items():
        for _ in range(count):
            n += 1
            DeliveryStop.objects.create(
                session=child,
                name=f"{name}-{n}",
                raw_address=f"{zip_code} Budapest" if zip_code else "no zip",
                postal_code=zip_code,
                lat=47.5,
                lng=19.05,
                geocode_status="success",
                **stop_kwargs,
            )
    return child


class FindZipConflictsTests(TestCase):
    def setUp(self):
        self.parent = DeliverySession.objects.create(name="Day", status="split")

    def test_a3_ac1_no_conflicts(self):
        a = _route(self.parent, "R1", {"1051": 3, "1052": 2})
        b = _route(self.parent, "R2", {"1061": 4})
        self.assertEqual(find_zip_conflicts([a, b]), [])
        self.assertEqual(find_zip_conflicts([]), [])

    def test_a3_ac2_one_conflict_lists_both_routes(self):
        a = _route(self.parent, "R1", {"1082": 4, "1051": 1})
        b = _route(self.parent, "R2", {"1082": 2})
        conflicts = find_zip_conflicts([a, b])
        self.assertEqual(len(conflicts), 1)
        c = conflicts[0]
        self.assertEqual((c["zip"], c["zone"]), ("1082", zones.zone_for_zip("1082")))
        self.assertEqual([(r["name"], r["count"]) for r in c["routes"]], [("R1", 4), ("R2", 2)])
        self.assertEqual({r["session_id"] for r in c["routes"]}, {str(a.id), str(b.id)})

    def test_a3_ac3_excluded_stops_ignored(self):
        a = _route(self.parent, "R1", {"1082": 2})
        b = _route(self.parent, "R2", {"1082": 1}, excluded=True)
        self.assertEqual(find_zip_conflicts([a, b]), [])

    def test_a3_ac4_stops_without_zip_never_conflict(self):
        a = _route(self.parent, "R1", {"": 3})
        b = _route(self.parent, "R2", {"": 2})
        self.assertEqual(find_zip_conflicts([a, b]), [])

    def test_a3_zip_outside_zone_config_has_no_zone(self):
        a = _route(self.parent, "R1", {"1111": 1})
        b = _route(self.parent, "R2", {"1111": 1})
        self.assertIsNone(find_zip_conflicts([a, b])[0]["zone"])

    def test_a3_three_routes_one_zip(self):
        routes = [_route(self.parent, f"R{i}", {"1054": i}) for i in (1, 2, 3)]
        conflicts = find_zip_conflicts(routes)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(len(conflicts[0]["routes"]), 3)


class ZipConflictsAPITests(TestCase):
    def setUp(self):
        self.planner, self.client = _make_planner("a3_planner")
        self.parent = DeliverySession.objects.create(name="Day", status="split")
        self.r1 = _route(self.parent, "R1", {"1082": 3, "1051": 2})
        self.r2 = _route(self.parent, "R2", {"1061": 2})

    def _move(self, stop, source, target):
        return self.client.post(
            f"/api/sessions/{source.id}/move-stop/",
            {"stop_id": stop.id, "to_session_id": str(target.id)},
            format="json",
        )

    def test_a3_ac5_move_creates_then_resolves_conflict(self):
        stop = self.r1.stops.filter(postal_code="1082").first()
        resp = self._move(stop, self.r1, self.r2)
        self.assertEqual(resp.status_code, 200)
        conflicts = resp.json()["zip_conflicts"]
        self.assertEqual([c["zip"] for c in conflicts], ["1082"])
        self.assertEqual(sorted(r["count"] for r in conflicts[0]["routes"]), [1, 2])

        # Parent GET reports the same conflict.
        detail = self.client.get(f"/api/sessions/{self.parent.id}/").json()
        self.assertEqual([c["zip"] for c in detail["zip_conflicts"]], ["1082"])

        # Move it back: resolved.
        resp = self._move(stop, self.r2, self.r1)
        self.assertEqual(resp.json()["zip_conflicts"], [])
        self.assertEqual(self.client.get(f"/api/sessions/{self.parent.id}/").json()["zip_conflicts"], [])

    def test_a3_plain_session_has_empty_conflicts(self):
        solo = DeliverySession.objects.create(name="Solo")
        self.assertEqual(self.client.get(f"/api/sessions/{solo.id}/").json()["zip_conflicts"], [])

    def test_a3_cluster_response_contains_zip_conflicts_field(self):
        session = DeliverySession.objects.create(name="Fresh", status="not_started")
        for i in range(6):
            DeliveryStop.objects.create(
                session=session,
                name=f"S{i}",
                raw_address="1051 Budapest",
                postal_code="1051",
                lat=47.5 + i * 0.001,
                lng=19.05,
                geocode_status="success",
            )
        resp = self.client.post(f"/api/sessions/{session.id}/cluster/", {"n_routes": 2}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["zip_conflicts"], [])  # A2 keeps the zip whole

    @override_settings(E2E_MOCK=True)
    def test_a3_ac7_conflict_does_not_block_optimize(self):
        stop = self.r1.stops.filter(postal_code="1082").first()
        self._move(stop, self.r1, self.r2)  # now conflicted
        resp = self.client.post(f"/api/sessions/{self.r2.id}/optimize/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_a3_biker_cannot_move_stop(self):
        _, biker_client = _make_biker("a3_biker")
        stop = self.r1.stops.first()
        resp = biker_client.post(
            f"/api/sessions/{self.r1.id}/move-stop/",
            {"stop_id": stop.id, "to_session_id": str(self.r2.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
