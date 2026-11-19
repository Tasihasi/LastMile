"""A4: move every stop of a postal code (or zone) to one sub-route."""

from unittest.mock import patch

from django.test import TestCase

from . import zones
from .models import DeliverySession, DeliveryStop
from .tests import _make_biker, _make_planner


class MoveZipAPITest(TestCase):
    def setUp(self):
        self.planner, self.client_ = _make_planner("a4_planner")
        self.parent = DeliverySession.objects.create(name="A4 day", status="split")
        self.routes = [
            DeliverySession.objects.create(name=f"R{i}", parent=self.parent, status="not_started") for i in range(3)
        ]
        # 1082 is split over R0 (3) and R1 (2); 1081 only on R0; 1083 only on R2.
        layout = [(0, "1082", 3), (1, "1082", 2), (0, "1081", 4), (2, "1083", 5), (1, "1085", 1)]
        for r, zip_code, count in layout:
            for i in range(count):
                DeliveryStop.objects.create(
                    session=self.routes[r],
                    name=f"{zip_code}-{r}-{i}",
                    raw_address=f"{zip_code} Budapest",
                    postal_code=zip_code,
                    lat=47.49,
                    lng=19.05,
                    geocode_status="success",
                    sequence_order=i + 1,
                )
        for r in self.routes:
            r.total_duration = 100
            r.route_geometry = [[0, 0]]
            r.save()

    def _post(self, payload, client=None):
        return (client or self.client_).post(f"/api/sessions/{self.parent.id}/move-zip/", payload, format="json")

    def _zip_routes(self, zip_code):
        return set(DeliveryStop.objects.filter(postal_code=zip_code).values_list("session_id", flat=True))

    def test_ac1_zip_ends_up_whole_in_target_and_conflict_clears(self):
        resp = self._post({"zip": "1082", "to_session_id": str(self.routes[0].id)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._zip_routes("1082"), {self.routes[0].id})
        body = resp.json()
        self.assertEqual(body["moved_count"], 2)
        self.assertEqual(body["zip_conflicts"], [])
        self.assertEqual(body["counts"][str(self.routes[0].id)], 9)

    def test_ac2_other_zips_untouched(self):
        self._post({"zip": "1082", "to_session_id": str(self.routes[0].id)})
        self.assertEqual(self._zip_routes("1081"), {self.routes[0].id})
        self.assertEqual(self._zip_routes("1083"), {self.routes[2].id})
        self.assertEqual(self._zip_routes("1085"), {self.routes[1].id})

    def test_ac3_touched_routes_lose_optimization_untouched_keep_it(self):
        self._post({"zip": "1082", "to_session_id": str(self.routes[0].id)})
        for r in self.routes:
            r.refresh_from_db()
        self.assertIsNone(self.routes[0].total_duration)
        self.assertIsNone(self.routes[1].total_duration)
        self.assertEqual(self.routes[2].total_duration, 100)
        self.assertTrue(DeliveryStop.objects.filter(session=self.routes[0], sequence_order=None).count() >= 2)
        self.assertFalse(DeliveryStop.objects.filter(session=self.routes[2], sequence_order=None).exists())

    def test_ac4_zone_variant_moves_all_zips_of_zone(self):
        zone_zips = zones.zips_in_zone(zones.zone_for_zip("1082"))
        # Put a second zip of the same zone on another route.
        other = next(z for z in zone_zips if z != "1082")
        DeliveryStop.objects.create(
            session=self.routes[2], name="o", raw_address=other, postal_code=other, lat=47.5, lng=19.0
        )
        resp = self._post({"zone_id": zones.zone_for_zip("1082"), "to_session_id": str(self.routes[1].id)})
        self.assertEqual(resp.status_code, 200)
        for z in ("1082", other):
            self.assertEqual(self._zip_routes(z), {self.routes[1].id})
        self.assertIn(other, resp.json()["moved_zips"])

    def test_ac5_validation(self):
        target = str(self.routes[0].id)
        self.assertEqual(self._post({"zip": "1082", "zone_id": "Z01", "to_session_id": target}).status_code, 400)
        self.assertEqual(self._post({"to_session_id": target}).status_code, 400)
        self.assertEqual(self._post({"zone_id": "nope", "to_session_id": target}).status_code, 400)
        resp = self._post({"zip": "9999", "to_session_id": target})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("9999", resp.json()["error"])
        stranger = DeliverySession.objects.create(name="other")
        self.assertEqual(self._post({"zip": "1082", "to_session_id": str(stranger.id)}).status_code, 404)

    def test_ac6_in_progress_or_finished_blocks_and_changes_nothing(self):
        for state, role in (("in_progress", "source"), ("finished", "target")):
            DeliverySession.objects.filter(parent=self.parent).update(status="not_started")
            blocked = self.routes[1] if role == "source" else self.routes[0]
            blocked.status = state
            blocked.save()
            resp = self._post({"zip": "1082", "to_session_id": str(self.routes[0].id)})
            self.assertEqual(resp.status_code, 400, state)
            self.assertEqual(self._zip_routes("1082"), {self.routes[0].id, self.routes[1].id})

    def test_ac6_untouched_in_progress_route_does_not_block(self):
        self.routes[2].status = "in_progress"
        self.routes[2].save()
        resp = self._post({"zip": "1082", "to_session_id": str(self.routes[0].id)})
        self.assertEqual(resp.status_code, 200)

    def test_ac7_permissions(self):
        _, biker_client = _make_biker("a4_biker")
        resp = self._post({"zip": "1082", "to_session_id": str(self.routes[0].id)}, client=biker_client)
        self.assertEqual(resp.status_code, 403)

    def test_ac8_atomic_on_failure(self):
        before = {s.id: s.session_id for s in DeliveryStop.objects.all()}
        with (
            patch.object(DeliverySession, "save", side_effect=RuntimeError("boom")),
            self.assertRaises(RuntimeError),
        ):
            self._post({"zip": "1082", "to_session_id": str(self.routes[0].id)})
        after = {s.id: s.session_id for s in DeliveryStop.objects.all()}
        self.assertEqual(before, after)

    def test_excluded_stops_stay_put(self):
        DeliveryStop.objects.filter(session=self.routes[1], postal_code="1082").update(excluded=True)
        self._post({"zip": "1082", "to_session_id": str(self.routes[0].id)})
        self.assertEqual(DeliveryStop.objects.filter(session=self.routes[1], postal_code="1082").count(), 2)

    def test_not_split_parent_is_400(self):
        plain = DeliverySession.objects.create(name="plain")
        resp = self.client_.post(
            f"/api/sessions/{plain.id}/move-zip/", {"zip": "1082", "to_session_id": str(plain.id)}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
