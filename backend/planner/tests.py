import io
import os
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import DeliverySession, DeliveryStop, SharedRoute, UserProfile
from .parsers import parse_csv, parse_file, parse_txt, parse_xlsx, parse_xml
from .serializers import ActiveSessionSerializer, SessionListSerializer

# ============================================
# Helpers
# ============================================


def _make_biker(username="biker1"):
    """Create a biker user with profile and token. Returns (user, client)."""
    user = User.objects.create_user(username=username)
    UserProfile.objects.create(user=user, role="biker")
    token = Token.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return user, client


def _make_planner(username="planner1"):
    """Create a planner user with profile and token. Returns (user, client)."""
    user = User.objects.create_user(username=username)
    UserProfile.objects.create(user=user, role="planner")
    token = Token.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return user, client


def _make_optimized_session(owner, num_stops=3):
    """Create a session with geocoded, optimized stops ready to start."""
    session = DeliverySession.objects.create(owner=owner, name="Test Route", status="not_started")
    stops = []
    for i in range(num_stops):
        stops.append(
            DeliveryStop(
                session=session,
                name=f"Stop {i + 1}",
                raw_address=f"Address {i + 1}",
                lat=47.5 + i * 0.01,
                lng=19.08 + i * 0.01,
                geocode_status="success",
                sequence_order=i + 1,
            )
        )
    DeliveryStop.objects.bulk_create(stops)
    return session


# ============================================
# Priority 1: Route Lifecycle Tests
# ============================================


class RouteLifecycleTest(TestCase):
    def setUp(self):
        self.user, self.client = _make_biker("route_biker")
        self.session = _make_optimized_session(self.user, num_stops=3)

    def test_start_route_happy_path(self):
        response = self.client.patch(f"/api/sessions/{self.session.id}/start/")
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "in_progress")
        self.assertIsNotNone(self.session.started_at)
        self.assertEqual(self.session.current_stop_index, 1)

    def test_start_route_already_started(self):
        self.session.status = "in_progress"
        self.session.save(update_fields=["status"])
        response = self.client.patch(f"/api/sessions/{self.session.id}/start/")
        self.assertEqual(response.status_code, 400)

    def test_start_route_not_optimized(self):
        self.session.stops.update(sequence_order=None)
        response = self.client.patch(f"/api/sessions/{self.session.id}/start/")
        self.assertEqual(response.status_code, 400)

    def test_start_route_session_not_found(self):
        response = self.client.patch("/api/sessions/00000000-0000-0000-0000-000000000000/start/")
        self.assertEqual(response.status_code, 404)

    def test_update_stop_delivered(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        stop = self.session.stops.get(sequence_order=1)
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/stops/{stop.id}/status/",
            {"status": "delivered"},
        )
        self.assertEqual(response.status_code, 200)
        stop.refresh_from_db()
        self.assertEqual(stop.delivery_status, "delivered")

    def test_update_stop_not_received(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        stop = self.session.stops.get(sequence_order=1)
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/stops/{stop.id}/status/",
            {"status": "not_received"},
        )
        self.assertEqual(response.status_code, 200)
        stop.refresh_from_db()
        self.assertEqual(stop.delivery_status, "not_received")

    def test_update_stop_skipped(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        stop = self.session.stops.get(sequence_order=1)
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/stops/{stop.id}/status/",
            {"status": "skipped"},
        )
        self.assertEqual(response.status_code, 200)
        stop.refresh_from_db()
        self.assertEqual(stop.delivery_status, "skipped")

    def test_update_stop_invalid_status(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        stop = self.session.stops.get(sequence_order=1)
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/stops/{stop.id}/status/",
            {"status": "lost_in_space"},
        )
        self.assertEqual(response.status_code, 400)

    def test_update_stop_auto_advance(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        stop1 = self.session.stops.get(sequence_order=1)
        self.client.patch(
            f"/api/sessions/{self.session.id}/stops/{stop1.id}/status/",
            {"status": "delivered"},
        )
        self.session.refresh_from_db()
        self.assertEqual(self.session.current_stop_index, 2)

    def test_update_stop_auto_finish(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        for stop in self.session.stops.order_by("sequence_order"):
            self.client.patch(
                f"/api/sessions/{self.session.id}/stops/{stop.id}/status/",
                {"status": "delivered"},
            )
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "finished")
        self.assertIsNotNone(self.session.finished_at)
        self.assertIsNone(self.session.current_stop_index)

    def test_update_stop_not_found(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        response = self.client.patch(
            f"/api/sessions/{self.session.id}/stops/999999/status/",
            {"status": "delivered"},
        )
        self.assertEqual(response.status_code, 404)


# ============================================
# Priority 2: Auth & Role Enforcement Tests
# ============================================


class AuthEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_login_creates_user_and_token(self):
        response = self.client.post("/api/auth/login/", {"username": "newbiker", "role": "biker"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["username"], "newbiker")
        self.assertEqual(data["user"]["role"], "biker")
        self.assertTrue(User.objects.filter(username="newbiker").exists())

    def test_login_existing_user(self):
        self.client.post("/api/auth/login/", {"username": "existuser", "role": "biker"})
        response = self.client.post("/api/auth/login/", {"username": "existuser", "role": "biker"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="existuser").count(), 1)

    def test_login_role_switch(self):
        self.client.post("/api/auth/login/", {"username": "switcher", "role": "biker"})
        self.client.post("/api/auth/login/", {"username": "switcher", "role": "planner"})
        profile = UserProfile.objects.get(user__username="switcher")
        self.assertEqual(profile.role, "planner")

    def test_login_empty_username(self):
        response = self.client.post("/api/auth/login/", {"username": "", "role": "biker"})
        self.assertEqual(response.status_code, 400)

    def test_login_invalid_role(self):
        response = self.client.post("/api/auth/login/", {"username": "baduser", "role": "admin"})
        self.assertEqual(response.status_code, 400)

    def test_me_returns_user(self):
        user, client = _make_biker("meuser")
        response = client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "meuser")
        self.assertEqual(response.json()["role"], "biker")

    def test_me_unauthenticated(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_logout_deletes_token(self):
        user, client = _make_biker("logoutuser")
        response = client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Token.objects.filter(user=user).exists())


class RoleEnforcementTest(TestCase):
    def setUp(self):
        self.biker_a, self.client_a = _make_biker("rbac_biker_a")
        self.biker_b, self.client_b = _make_biker("rbac_biker_b")
        self.planner, self.planner_client = _make_planner("rbac_planner")

    def test_biker_cannot_access_other_bikers_session(self):
        session = DeliverySession.objects.create(owner=self.biker_a, name="A's route")
        response = self.client_b.get(f"/api/sessions/{session.id}/")
        self.assertEqual(response.status_code, 404)

    def test_planner_can_access_any_session(self):
        session = DeliverySession.objects.create(owner=self.biker_a, name="A's route")
        response = self.planner_client.get(f"/api/sessions/{session.id}/")
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_upload_rejected(self):
        client = APIClient()
        f = SimpleUploadedFile("stops.csv", b"name,address\nShop,Main St\n", content_type="text/csv")
        response = client.post("/api/upload/", {"file": f}, format="multipart")
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_sessions_rejected(self):
        client = APIClient()
        response = client.get("/api/sessions/")
        self.assertEqual(response.status_code, 401)


# ============================================
# Priority 3: Planner Management Tests
# ============================================


class PlannerManagementTest(TestCase):
    def setUp(self):
        self.planner, self.planner_client = _make_planner("mgmt_planner")
        self.biker, self.biker_client = _make_biker("mgmt_biker")
        self.session = DeliverySession.objects.create(owner=self.biker, name="Biker Route")

    def test_planner_delete_session(self):
        response = self.planner_client.delete(f"/api/sessions/{self.session.id}/delete/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(DeliverySession.objects.filter(id=self.session.id).exists())

    def test_biker_cannot_delete_session(self):
        response = self.biker_client.delete(f"/api/sessions/{self.session.id}/delete/")
        self.assertEqual(response.status_code, 403)

    def test_delete_session_not_found(self):
        response = self.planner_client.delete("/api/sessions/00000000-0000-0000-0000-000000000000/delete/")
        self.assertEqual(response.status_code, 404)

    def test_planner_assign_session(self):
        biker2, _ = _make_biker("assign_target")
        response = self.planner_client.patch(
            f"/api/sessions/{self.session.id}/assign/",
            {"owner_id": biker2.id},
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.owner, biker2)

    def test_unassign_session(self):
        """Sending no owner_id unassigns the session."""
        response = self.planner_client.patch(f"/api/sessions/{self.session.id}/assign/", {})
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertIsNone(self.session.owner)

    def test_assign_user_not_found(self):
        response = self.planner_client.patch(
            f"/api/sessions/{self.session.id}/assign/",
            {"owner_id": 99999},
        )
        self.assertEqual(response.status_code, 404)

    def test_biker_cannot_assign(self):
        response = self.biker_client.patch(
            f"/api/sessions/{self.session.id}/assign/",
            {"owner_id": self.biker.id},
        )
        self.assertEqual(response.status_code, 403)

    def test_planner_rename_session(self):
        response = self.planner_client.patch(
            f"/api/sessions/{self.session.id}/rename/",
            {"name": "New Name"},
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.name, "New Name")

    def test_rename_empty_name(self):
        response = self.planner_client.patch(
            f"/api/sessions/{self.session.id}/rename/",
            {"name": ""},
        )
        self.assertEqual(response.status_code, 400)

    def test_biker_cannot_rename(self):
        response = self.biker_client.patch(
            f"/api/sessions/{self.session.id}/rename/",
            {"name": "Hacked"},
        )
        self.assertEqual(response.status_code, 403)


class SessionListingTest(TestCase):
    def setUp(self):
        self.biker_a, self.client_a = _make_biker("list_biker_a")
        self.biker_b, self.client_b = _make_biker("list_biker_b")
        self.planner, self.planner_client = _make_planner("list_planner")
        DeliverySession.objects.create(owner=self.biker_a, name="A1")
        DeliverySession.objects.create(owner=self.biker_a, name="A2")
        DeliverySession.objects.create(owner=self.biker_b, name="B1")

    def test_biker_sees_only_own_sessions(self):
        response = self.client_a.get("/api/sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_planner_sees_all_sessions(self):
        response = self.planner_client.get("/api/sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_planner_filter_by_owner_id(self):
        response = self.planner_client.get(f"/api/sessions/?owner_id={self.biker_a.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)


# ============================================
# Priority 4: Sharing Tests
# ============================================


class SharingTest(TestCase):
    def setUp(self):
        self.user, self.client = _make_biker("share_biker")
        self.session = DeliverySession.objects.create(owner=self.user, name="Share Route")

    def test_create_share_link(self):
        response = self.client.post(f"/api/sessions/{self.session.id}/share/")
        self.assertEqual(response.status_code, 201)
        self.assertIn("share_id", response.json())

    def test_get_shared_route(self):
        share = SharedRoute.objects.create(session=self.session)
        anon_client = APIClient()
        response = anon_client.get(f"/api/shared/{share.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["session"]["name"], "Share Route")

    def test_shared_route_not_found(self):
        anon_client = APIClient()
        response = anon_client.get("/api/shared/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, 404)

    def test_share_session_not_found(self):
        response = self.client.post("/api/sessions/00000000-0000-0000-0000-000000000000/share/")
        self.assertEqual(response.status_code, 404)


# ============================================
# Priority 5: XLSX Parsing Tests
# ============================================


class ParserXLSXTest(TestCase):
    def _make_xlsx(self, headers, data_rows):
        """Create an in-memory XLSX file."""
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for row in data_rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    def test_parse_xlsx_basic(self):
        f = self._make_xlsx(["name", "address"], [["Shop A", "Main St"], ["Shop B", "Vaci ut"]])
        rows = parse_xlsx(f)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "Shop A")
        self.assertEqual(rows[0]["address"], "Main St")

    def test_parse_xlsx_with_delivery_details(self):
        f = self._make_xlsx(
            ["name", "address", "product_code", "recipient_name", "recipient_phone"],
            [["Shop A", "Main St", "PKG-001", "John Doe", "+36301234567"]],
        )
        rows = parse_xlsx(f)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_code"], "PKG-001")
        self.assertEqual(rows[0]["recipient_name"], "John Doe")
        self.assertEqual(rows[0]["recipient_phone"], "+36301234567")


# ============================================
# Priority 6: Geocoder & Optimizer Mocked Tests
# ============================================


class GeocoderTest(TestCase):
    @patch("planner.geocoder.time")
    @patch("planner.geocoder.requests.get")
    def test_geocode_success(self, mock_get, mock_time):
        mock_time.monotonic.return_value = 100.0
        mock_response = MagicMock()
        mock_response.json.return_value = [{"lat": "47.5", "lon": "19.08"}]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from .geocoder import geocode_address

        result = geocode_address("Main St Budapest")
        self.assertEqual(result, (47.5, 19.08))

    @patch("planner.geocoder.time")
    @patch("planner.geocoder.requests.get")
    def test_geocode_not_found(self, mock_get, mock_time):
        mock_time.monotonic.return_value = 100.0
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from .geocoder import geocode_address

        result = geocode_address("Nonexistent place xyz")
        self.assertIsNone(result)

    @patch("planner.geocoder.time")
    @patch("planner.geocoder.requests.get")
    def test_geocode_request_failure(self, mock_get, mock_time):
        import requests

        mock_time.monotonic.return_value = 100.0
        mock_get.side_effect = requests.RequestException("Connection error")

        from .geocoder import geocode_address

        result = geocode_address("Some address")
        self.assertIsNone(result)


class OptimizerTest(TestCase):
    def _make_stop(self, stop_id, lat, lng):
        """Create a mock stop object."""
        stop = MagicMock()
        stop.id = stop_id
        stop.lat = lat
        stop.lng = lng
        return stop

    @patch("planner.optimizer.requests.post")
    def test_optimize_route_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "routes": [
                {
                    "steps": [
                        {"type": "start"},
                        {"type": "job", "job": 2},
                        {"type": "job", "job": 1},
                        {"type": "end"},
                    ]
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from .optimizer import optimize_route

        stops = [self._make_stop(1, 47.5, 19.08), self._make_stop(2, 47.51, 19.09)]
        result = optimize_route(stops)
        self.assertEqual(result, [2, 1])

    @patch("planner.optimizer.requests.post")
    def test_get_route_details_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "features": [
                {
                    "geometry": {"type": "LineString", "coordinates": [[19.08, 47.5], [19.09, 47.51]]},
                    "properties": {
                        "segments": [
                            {"duration": 120.4, "distance": 1500.7},
                        ]
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from .optimizer import get_route_details

        stops = [self._make_stop(1, 47.5, 19.08), self._make_stop(2, 47.51, 19.09)]
        result = get_route_details(stops)
        self.assertIsNotNone(result)
        self.assertEqual(result["total_duration"], 120)
        self.assertEqual(result["total_distance"], 1501)
        self.assertEqual(result["geometry"]["type"], "LineString")
        self.assertEqual(len(result["segments"]), 1)

    def test_optimize_fewer_than_2_stops(self):
        from .optimizer import optimize_route

        stop = self._make_stop(42, 47.5, 19.08)
        result = optimize_route([stop])
        self.assertEqual(result, [42])


class OptimizeAPIKeyTest(TestCase):
    """Test that missing or invalid ORS_API_KEY gives clear user-facing errors."""

    def setUp(self):
        self.user, self.client = _make_biker("ors_biker")
        self.session = _make_optimized_session(self.user, num_stops=3)

    @patch("planner.views.django_settings")
    def test_optimize_missing_api_key(self, mock_settings):
        mock_settings.ORS_API_KEY = ""
        response = self.client.post(f"/api/sessions/{self.session.id}/optimize/")
        self.assertEqual(response.status_code, 503)
        error = response.json()["error"]
        self.assertIn("ORS_API_KEY", error)
        self.assertIn("not configured", error)

    @patch("planner.views.optimize_route")
    def test_optimize_invalid_api_key(self, mock_optimize):
        mock_response = MagicMock()
        mock_response.status_code = 403
        import requests

        mock_optimize.side_effect = requests.HTTPError("403 Forbidden", response=mock_response)
        response = self.client.post(f"/api/sessions/{self.session.id}/optimize/")
        self.assertEqual(response.status_code, 502)
        error = response.json()["error"]
        self.assertIn("ORS_API_KEY", error)
        self.assertIn("invalid or expired", error)

    @patch("planner.views.optimize_route")
    def test_optimize_unauthorized_api_key(self, mock_optimize):
        mock_response = MagicMock()
        mock_response.status_code = 401
        import requests

        mock_optimize.side_effect = requests.HTTPError("401 Unauthorized", response=mock_response)
        response = self.client.post(f"/api/sessions/{self.session.id}/optimize/")
        self.assertEqual(response.status_code, 502)
        error = response.json()["error"]
        self.assertIn("ORS_API_KEY", error)


# ============================================
# Priority 7: Serializer Computed Field Tests
# ============================================


class SessionListSerializerTest(TestCase):
    def setUp(self):
        self.user, _ = _make_biker("serial_biker")
        self.session = _make_optimized_session(self.user, num_stops=3)

    def test_delivered_count(self):
        self.session.stops.filter(sequence_order=1).update(delivery_status="delivered")
        self.session.stops.filter(sequence_order=2).update(delivery_status="delivered")
        data = SessionListSerializer(self.session).data
        self.assertEqual(data["delivered_count"], 2)

    def test_not_received_count(self):
        self.session.stops.filter(sequence_order=1).update(delivery_status="not_received")
        data = SessionListSerializer(self.session).data
        self.assertEqual(data["not_received_count"], 1)

    def test_current_stop_name(self):
        self.session.current_stop_index = 2
        self.session.save(update_fields=["current_stop_index"])
        data = SessionListSerializer(self.session).data
        self.assertEqual(data["current_stop_name"], "Stop 2")

    def test_current_stop_name_none(self):
        self.session.current_stop_index = None
        self.session.save(update_fields=["current_stop_index"])
        data = SessionListSerializer(self.session).data
        self.assertIsNone(data["current_stop_name"])


class ActiveSessionSerializerTest(TestCase):
    def setUp(self):
        self.user, _ = _make_biker("active_serial_biker")
        self.session = _make_optimized_session(self.user, num_stops=4)

    def test_delivered_count_includes_all_done(self):
        """ActiveSessionSerializer counts delivered + not_received + skipped."""
        self.session.stops.filter(sequence_order=1).update(delivery_status="delivered")
        self.session.stops.filter(sequence_order=2).update(delivery_status="not_received")
        self.session.stops.filter(sequence_order=3).update(delivery_status="skipped")
        data = ActiveSessionSerializer(self.session).data
        self.assertEqual(data["delivered_count"], 3)


# ============================================
# Priority 8: Live Tracking Endpoint Tests
# ============================================


class LiveTrackingTest(TestCase):
    def setUp(self):
        self.planner, self.planner_client = _make_planner("live_planner")
        self.biker, self.biker_client = _make_biker("live_biker")

    def test_active_sessions_returns_in_progress(self):
        DeliverySession.objects.create(owner=self.biker, name="Active", status="in_progress")
        DeliverySession.objects.create(owner=self.biker, name="Done", status="finished")
        DeliverySession.objects.create(owner=self.biker, name="Waiting", status="not_started")
        response = self.planner_client.get("/api/sessions/active/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], "Active")

    def test_active_sessions_biker_rejected(self):
        response = self.biker_client.get("/api/sessions/active/")
        self.assertEqual(response.status_code, 403)

    def test_list_bikers(self):
        _make_biker("extra_biker1")
        _make_biker("extra_biker2")
        response = self.planner_client.get("/api/users/bikers/")
        self.assertEqual(response.status_code, 200)
        usernames = [u["username"] for u in response.json()]
        self.assertIn("live_biker", usernames)
        self.assertIn("extra_biker1", usernames)
        self.assertIn("extra_biker2", usernames)
        self.assertNotIn("live_planner", usernames)


# ============================================
# Priority 9: Fixed Existing Tests
# ============================================


class ParserCSVTest(TestCase):
    def test_parse_csv_with_addresses(self):
        content = b"name,address\nShop A,Main Street 1 Budapest\nShop B,Vaci ut 5 Budapest\n"
        rows = parse_csv(io.BytesIO(content))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "Shop A")
        self.assertEqual(rows[0]["address"], "Main Street 1 Budapest")
        self.assertIsNone(rows[0]["lat"])

    def test_parse_csv_with_coordinates(self):
        content = b"name,address,lat,lng\nDepot,,47.5,19.08\n"
        rows = parse_csv(io.BytesIO(content))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lat"], 47.5)
        self.assertEqual(rows[0]["lng"], 19.08)

    def test_parse_csv_mixed_input(self):
        content = b"name,address,lat,lng\nDepot,,47.5,19.08\nShop,Main St,,\n"
        rows = parse_csv(io.BytesIO(content))
        self.assertEqual(len(rows), 2)
        self.assertIsNotNone(rows[0]["lat"])
        self.assertIsNone(rows[1]["lat"])
        self.assertEqual(rows[1]["address"], "Main St")

    def test_parse_csv_skips_rows_without_name(self):
        content = b"name,address\n,Main St\nShop B,Vaci ut\n"
        rows = parse_csv(io.BytesIO(content))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Shop B")

    def test_parse_csv_skips_rows_without_address_or_coords(self):
        content = b"name,address,lat,lng\nShop A,,,\nShop B,Main St,,\n"
        rows = parse_csv(io.BytesIO(content))
        self.assertEqual(len(rows), 1)

    def test_parse_csv_bom_handling(self):
        content = b"\xef\xbb\xbfname,address\nShop A,Main St\n"
        rows = parse_csv(io.BytesIO(content))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Shop A")

    def test_parse_csv_with_delivery_details(self):
        content = b"name,address,lat,lng,product_code,recipient_name,recipient_phone\nShop A,Main St,,,PKG-001,John Doe,+36 30 123 4567\n"
        rows = parse_csv(io.BytesIO(content))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_code"], "PKG-001")
        self.assertEqual(rows[0]["recipient_name"], "John Doe")
        self.assertEqual(rows[0]["recipient_phone"], "+36 30 123 4567")

    def test_parse_csv_optional_delivery_details(self):
        content = b"name,address\nShop A,Main St\n"
        rows = parse_csv(io.BytesIO(content))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_code"], "")
        self.assertEqual(rows[0]["recipient_name"], "")
        self.assertEqual(rows[0]["recipient_phone"], "")


class ParserTXTTest(TestCase):
    def test_parse_txt_tab_delimited(self):
        # Fixed: removed dead variable with typo header
        content = b"name\taddress\tlat\tlng\nShop A\tMain St\t\t\n"
        rows = parse_txt(io.BytesIO(content))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Shop A")


class ParserXMLTest(TestCase):
    def test_parse_xml(self):
        content = b"""<deliveries>
            <stop><name>Shop A</name><address>Main St</address><lat></lat><lng></lng></stop>
            <stop><name>Depot</name><address></address><lat>47.5</lat><lng>19.08</lng></stop>
        </deliveries>"""
        rows = parse_xml(io.BytesIO(content))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "Shop A")
        self.assertEqual(rows[1]["lat"], 47.5)


class ParserDispatchTest(TestCase):
    def test_unsupported_format_raises(self):
        with self.assertRaises(ValueError):
            parse_file(io.BytesIO(b"data"), "file.pdf")

    def test_dispatch_csv(self):
        content = b"name,address\nShop,Main St\n"
        rows = parse_file(io.BytesIO(content), "stops.csv")
        self.assertEqual(len(rows), 1)


class SampleDataTest(TestCase):
    """Verify the bundled sample files parse correctly."""

    def _sample_path(self, filename):
        return os.path.join(os.path.dirname(__file__), "sample_data", filename)

    def test_sample_csv(self):
        with open(self._sample_path("budapest_deliveries.csv"), "rb") as f:
            rows = parse_csv(f)
        self.assertEqual(len(rows), 12)
        with_coords = [r for r in rows if r["lat"] is not None]
        self.assertEqual(len(with_coords), 3)

    def test_sample_txt(self):
        with open(self._sample_path("sample.txt"), "rb") as f:
            rows = parse_txt(f)
        self.assertEqual(len(rows), 5)

    def test_sample_xml(self):
        with open(self._sample_path("sample.xml"), "rb") as f:
            rows = parse_xml(f)
        self.assertEqual(len(rows), 5)


class UploadAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testbiker")
        UserProfile.objects.create(user=self.user, role="biker")
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_upload_csv(self):
        content = b"name,address\nShop A,Main St Budapest\nShop B,Vaci ut Budapest\n"
        f = SimpleUploadedFile("stops.csv", content, content_type="text/csv")
        response = self.client.post("/api/upload/", {"file": f}, format="multipart")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(len(data["stops"]), 2)
        self.assertTrue(data["needs_geocoding"])

    def test_upload_no_file(self):
        response = self.client.post("/api/upload/", {}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_upload_unsupported_format(self):
        f = SimpleUploadedFile("data.pdf", b"fake", content_type="application/pdf")
        response = self.client.post("/api/upload/", {"file": f}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_upload_csv_with_delivery_details(self):
        content = (
            b"name,address,product_code,recipient_name,recipient_phone\nShop A,Main St,PKG-001,John Doe,+36301234567\n"
        )
        f = SimpleUploadedFile("stops.csv", content, content_type="text/csv")
        response = self.client.post("/api/upload/", {"file": f}, format="multipart")
        self.assertEqual(response.status_code, 201)
        stop = response.json()["stops"][0]
        self.assertEqual(stop["product_code"], "PKG-001")
        self.assertEqual(stop["recipient_name"], "John Doe")
        self.assertEqual(stop["recipient_phone"], "+36301234567")

    def test_upload_empty_file(self):
        f = SimpleUploadedFile("stops.csv", b"name,address\n", content_type="text/csv")
        response = self.client.post("/api/upload/", {"file": f}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_upload_rejected(self):
        anon_client = APIClient()
        f = SimpleUploadedFile("stops.csv", b"name,address\nShop,Main St\n", content_type="text/csv")
        response = anon_client.post("/api/upload/", {"file": f}, format="multipart")
        self.assertEqual(response.status_code, 401)


class SessionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testbiker2")
        UserProfile.objects.create(user=self.user, role="biker")
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.session = DeliverySession.objects.create(owner=self.user)
        DeliveryStop.objects.create(
            session=self.session, name="Shop A", raw_address="Main St", geocode_status="pending"
        )
        DeliveryStop.objects.create(session=self.session, name="Depot", lat=47.5, lng=19.08, geocode_status="skipped")

    def test_get_session(self):
        response = self.client.get(f"/api/sessions/{self.session.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["stops"]), 2)
        self.assertTrue(data["needs_geocoding"])

    def test_get_session_not_found(self):
        response = self.client.get("/api/sessions/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, 404)

    def test_optimize_needs_minimum_stops(self):
        DeliveryStop.objects.filter(session=self.session, name="Shop A").update(lat=None, lng=None)
        response = self.client.post(f"/api/sessions/{self.session.id}/optimize/")
        self.assertEqual(response.status_code, 400)
