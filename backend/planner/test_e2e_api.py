"""
End-to-end API tests — exercises every endpoint with real parameters.
Tests the full request/response cycle including serialization, auth, and DB state.
"""

import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import DeliverySession, DeliveryStop, SharedRoute, UserProfile


# ============================================
# Helpers
# ============================================


def _login(client, username, role="biker"):
    """Login via the API and return the response data."""
    resp = client.post("/api/auth/login/", {"username": username, "role": role})
    return resp


def _auth_client(username, role="biker"):
    """Create a logged-in APIClient via the login endpoint."""
    client = APIClient()
    resp = _login(client, username, role)
    token = resp.json()["token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _upload_csv(client, csv_content, owner_id=None):
    """Upload a CSV file and return the response."""
    f = SimpleUploadedFile("test_stops.csv", csv_content, content_type="text/csv")
    data = {"file": f}
    if owner_id is not None:
        data["owner_id"] = owner_id
    return client.post("/api/upload/", data, format="multipart")


def _make_optimized_session(owner, num_stops=3):
    """Create a session with geocoded, optimized stops."""
    session = DeliverySession.objects.create(
        owner=owner, name="Test Route", status="not_started"
    )
    for i in range(num_stops):
        DeliveryStop.objects.create(
            session=session,
            name=f"Stop {i + 1}",
            raw_address=f"Address {i + 1}",
            lat=47.5 + i * 0.01,
            lng=19.08 + i * 0.01,
            geocode_status="success",
            sequence_order=i + 1,
        )
    return session


# ============================================
# E2E: Full Authentication Flow
# ============================================


class AuthFlowE2E(TestCase):
    """Test the complete auth lifecycle: login -> me -> logout -> me fails."""

    def test_full_auth_lifecycle(self):
        client = APIClient()

        # 1. Login as biker
        resp = _login(client, "e2e_biker", "biker")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["username"], "e2e_biker")
        self.assertEqual(data["user"]["role"], "biker")
        token = data["token"]

        # 2. Use token to call /auth/me/
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        resp = client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["username"], "e2e_biker")

        # 3. Logout
        resp = client.post("/api/auth/logout/")
        self.assertEqual(resp.status_code, 200)

        # 4. Token is now invalid
        resp = client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, 401)

    def test_login_as_planner(self):
        client = APIClient()
        resp = _login(client, "e2e_planner", "planner")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["user"]["role"], "planner")

    def test_login_same_user_different_role_switches(self):
        client = APIClient()
        _login(client, "switcher", "biker")
        _login(client, "switcher", "planner")
        profile = UserProfile.objects.get(user__username="switcher")
        self.assertEqual(profile.role, "planner")

    def test_login_empty_username_rejected(self):
        client = APIClient()
        resp = client.post("/api/auth/login/", {"username": "", "role": "biker"})
        self.assertEqual(resp.status_code, 400)

    def test_login_invalid_role_rejected(self):
        client = APIClient()
        resp = client.post("/api/auth/login/", {"username": "u", "role": "admin"})
        self.assertEqual(resp.status_code, 400)

    def test_login_missing_role_defaults_to_biker(self):
        client = APIClient()
        resp = client.post("/api/auth/login/", {"username": "norole"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["user"]["role"], "biker")


# ============================================
# E2E: Upload -> Get Session -> Verify Stops
# ============================================


class UploadAndSessionE2E(TestCase):
    """Test file upload with all parameter variations and session retrieval."""

    def setUp(self):
        self.biker = _auth_client("upload_biker", "biker")
        self.planner = _auth_client("upload_planner", "planner")

    def test_upload_csv_creates_session_with_stops(self):
        csv = b"name,address,lat,lng\nDepot,,47.5,19.08\nShop A,Main St Budapest,,\n"
        resp = _upload_csv(self.biker, csv)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], "Test Stops")  # auto-generated from filename
        self.assertEqual(len(data["stops"]), 2)
        self.assertTrue(data["needs_geocoding"])

        # Depot has coords -> skipped, Shop has address -> pending
        statuses = {s["name"]: s["geocode_status"] for s in data["stops"]}
        self.assertEqual(statuses["Depot"], "skipped")
        self.assertEqual(statuses["Shop A"], "pending")

    def test_upload_with_delivery_details(self):
        csv = b"name,address,product_code,recipient_name,recipient_phone\nShop,Main St,PKG-001,John,+361234567\n"
        resp = _upload_csv(self.biker, csv)
        self.assertEqual(resp.status_code, 201)
        stop = resp.json()["stops"][0]
        self.assertEqual(stop["product_code"], "PKG-001")
        self.assertEqual(stop["recipient_name"], "John")
        self.assertEqual(stop["recipient_phone"], "+361234567")

    def test_upload_all_coords_no_geocoding_needed(self):
        csv = b"name,address,lat,lng\nA,,47.5,19.08\nB,,47.51,19.09\n"
        resp = _upload_csv(self.biker, csv)
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(resp.json()["needs_geocoding"])

    def test_upload_no_file_rejected(self):
        resp = self.biker.post("/api/upload/", {}, format="multipart")
        self.assertEqual(resp.status_code, 400)

    def test_upload_empty_csv_rejected(self):
        csv = b"name,address\n"
        resp = _upload_csv(self.biker, csv)
        self.assertEqual(resp.status_code, 400)

    def test_upload_unsupported_format_rejected(self):
        f = SimpleUploadedFile("data.pdf", b"fake", content_type="application/pdf")
        resp = self.biker.post("/api/upload/", {"file": f}, format="multipart")
        self.assertEqual(resp.status_code, 400)

    def test_upload_unauthenticated_rejected(self):
        anon = APIClient()
        csv = b"name,address\nShop,Main St\n"
        f = SimpleUploadedFile("s.csv", csv, content_type="text/csv")
        resp = anon.post("/api/upload/", {"file": f}, format="multipart")
        self.assertEqual(resp.status_code, 401)

    def test_planner_upload_for_biker(self):
        biker_user = User.objects.get(username="upload_biker")
        csv = b"name,address,lat,lng\nA,,47.5,19.08\n"
        resp = _upload_csv(self.planner, csv, owner_id=biker_user.id)
        self.assertEqual(resp.status_code, 201)
        session = DeliverySession.objects.get(id=resp.json()["id"])
        self.assertEqual(session.owner, biker_user)

    def test_get_session_returns_full_data(self):
        csv = b"name,address,lat,lng\nA,,47.5,19.08\nB,,47.51,19.09\n"
        upload_resp = _upload_csv(self.biker, csv)
        session_id = upload_resp.json()["id"]

        resp = self.biker.get(f"/api/sessions/{session_id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["stops"]), 2)
        self.assertIn("route_geometry", data)
        self.assertIn("route_segments", data)
        self.assertEqual(data["status"], "not_started")

    def test_get_session_not_found(self):
        resp = self.biker.get("/api/sessions/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, 404)

    def test_get_session_unauthenticated(self):
        anon = APIClient()
        resp = anon.get("/api/sessions/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, 401)


# ============================================
# E2E: Session Listing with Filters
# ============================================


class SessionListingE2E(TestCase):
    """Test session listing with role-based visibility and filters."""

    def setUp(self):
        self.biker_a = _auth_client("list_a", "biker")
        self.biker_b = _auth_client("list_b", "biker")
        self.planner = _auth_client("list_planner", "planner")

        user_a = User.objects.get(username="list_a")
        user_b = User.objects.get(username="list_b")
        DeliverySession.objects.create(owner=user_a, name="A1")
        DeliverySession.objects.create(owner=user_a, name="A2")
        DeliverySession.objects.create(owner=user_b, name="B1")

    def test_biker_sees_only_own(self):
        resp = self.biker_a.get("/api/sessions/")
        self.assertEqual(resp.status_code, 200)
        names = [s["name"] for s in resp.json()]
        self.assertEqual(len(names), 2)
        self.assertIn("A1", names)
        self.assertNotIn("B1", names)

    def test_planner_sees_all(self):
        resp = self.planner.get("/api/sessions/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 3)

    def test_planner_filter_by_owner_id(self):
        user_a = User.objects.get(username="list_a")
        resp = self.planner.get(f"/api/sessions/?owner_id={user_a.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)
        for s in resp.json():
            self.assertEqual(s["owner_name"], "list_a")

    def test_session_list_response_shape(self):
        resp = self.planner.get("/api/sessions/")
        session = resp.json()[0]
        expected_fields = [
            "id", "name", "created_at", "owner_name", "stop_count",
            "total_duration", "total_distance", "status", "started_at",
            "finished_at", "current_stop_index", "delivered_count",
            "not_received_count", "current_stop_name",
        ]
        for field in expected_fields:
            self.assertIn(field, session, f"Missing field: {field}")


# ============================================
# E2E: Geocode Status
# ============================================


class GeocodeStatusE2E(TestCase):
    """Test the geocode-status endpoint."""

    def setUp(self):
        self.client = _auth_client("geo_biker", "biker")
        user = User.objects.get(username="geo_biker")
        self.session = DeliverySession.objects.create(owner=user, name="Geo Route")
        DeliveryStop.objects.create(
            session=self.session, name="A", raw_address="Addr",
            geocode_status="pending",
        )
        DeliveryStop.objects.create(
            session=self.session, name="B", lat=47.5, lng=19.08,
            geocode_status="skipped",
        )
        DeliveryStop.objects.create(
            session=self.session, name="C", lat=47.51, lng=19.09,
            geocode_status="success",
        )

    def test_geocode_status_counts(self):
        resp = self.client.get(f"/api/sessions/{self.session.id}/geocode-status/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["pending"], 1)
        self.assertEqual(data["success"], 1)
        self.assertEqual(data["failed"], 0)
        self.assertEqual(len(data["stops"]), 3)

    def test_geocode_status_not_found(self):
        resp = self.client.get("/api/sessions/00000000-0000-0000-0000-000000000000/geocode-status/")
        self.assertEqual(resp.status_code, 404)

    def test_geocode_no_pending_stops(self):
        resp = self.client.post(f"/api/sessions/{self.session.id}/geocode/")
        # Even if geocode runs, it should not error for session with pending stops
        # (actual geocoding would hit Nominatim, but we're testing the endpoint logic)
        self.assertIn(resp.status_code, [200])


# ============================================
# E2E: Planner Management (assign, unassign, rename, delete)
# ============================================


class PlannerManagementE2E(TestCase):
    """Test all planner management actions with full parameter coverage."""

    def setUp(self):
        self.planner = _auth_client("mgmt_planner", "planner")
        self.biker = _auth_client("mgmt_biker", "biker")
        self.biker2 = _auth_client("mgmt_biker2", "biker")

        user = User.objects.get(username="mgmt_biker")
        self.session = DeliverySession.objects.create(owner=user, name="Original Name")

    # --- Assign ---

    def test_assign_to_different_biker(self):
        biker2_user = User.objects.get(username="mgmt_biker2")
        resp = self.planner.patch(
            f"/api/sessions/{self.session.id}/assign/",
            {"owner_id": biker2_user.id},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["owner_name"], "mgmt_biker2")
        self.session.refresh_from_db()
        self.assertEqual(self.session.owner, biker2_user)

    def test_unassign_with_null_owner_id(self):
        resp = self.planner.patch(
            f"/api/sessions/{self.session.id}/assign/",
            {"owner_id": None},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["owner_name"])
        self.session.refresh_from_db()
        self.assertIsNone(self.session.owner)

    def test_unassign_with_empty_body(self):
        resp = self.planner.patch(f"/api/sessions/{self.session.id}/assign/", {})
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        self.assertIsNone(self.session.owner)

    def test_assign_nonexistent_user(self):
        resp = self.planner.patch(
            f"/api/sessions/{self.session.id}/assign/",
            {"owner_id": 99999},
        )
        self.assertEqual(resp.status_code, 404)

    def test_assign_nonexistent_session(self):
        resp = self.planner.patch(
            "/api/sessions/00000000-0000-0000-0000-000000000000/assign/",
            {"owner_id": 1},
        )
        self.assertEqual(resp.status_code, 404)

    def test_biker_cannot_assign(self):
        resp = self.biker.patch(
            f"/api/sessions/{self.session.id}/assign/",
            {"owner_id": 1},
        )
        self.assertEqual(resp.status_code, 403)

    # --- Rename ---

    def test_rename_session(self):
        resp = self.planner.patch(
            f"/api/sessions/{self.session.id}/rename/",
            {"name": "New Name"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "New Name")
        self.session.refresh_from_db()
        self.assertEqual(self.session.name, "New Name")

    def test_rename_empty_rejected(self):
        resp = self.planner.patch(
            f"/api/sessions/{self.session.id}/rename/",
            {"name": ""},
        )
        self.assertEqual(resp.status_code, 400)

    def test_rename_whitespace_only_rejected(self):
        resp = self.planner.patch(
            f"/api/sessions/{self.session.id}/rename/",
            {"name": "   "},
        )
        self.assertEqual(resp.status_code, 400)

    def test_rename_nonexistent_session(self):
        resp = self.planner.patch(
            "/api/sessions/00000000-0000-0000-0000-000000000000/rename/",
            {"name": "X"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_biker_cannot_rename(self):
        resp = self.biker.patch(
            f"/api/sessions/{self.session.id}/rename/",
            {"name": "Hacked"},
        )
        self.assertEqual(resp.status_code, 403)

    # --- Delete ---

    def test_delete_session(self):
        resp = self.planner.delete(f"/api/sessions/{self.session.id}/delete/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(DeliverySession.objects.filter(id=self.session.id).exists())

    def test_delete_nonexistent_session(self):
        resp = self.planner.delete("/api/sessions/00000000-0000-0000-0000-000000000000/delete/")
        self.assertEqual(resp.status_code, 404)

    def test_biker_cannot_delete(self):
        resp = self.biker.delete(f"/api/sessions/{self.session.id}/delete/")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(DeliverySession.objects.filter(id=self.session.id).exists())


# ============================================
# E2E: Route Lifecycle (start -> deliver all -> finish)
# ============================================


class RouteLifecycleE2E(TestCase):
    """Full route lifecycle: start -> mark each stop -> auto-finish."""

    def setUp(self):
        self.client = _auth_client("lifecycle_biker", "biker")
        user = User.objects.get(username="lifecycle_biker")
        self.session = _make_optimized_session(user, num_stops=3)

    def test_full_delivery_lifecycle(self):
        sid = self.session.id

        # 1. Start route
        resp = self.client.patch(f"/api/sessions/{sid}/start/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "in_progress")
        self.assertIsNotNone(data["started_at"])
        self.assertEqual(data["current_stop_index"], 1)

        # 2. Deliver stop 1
        stop1 = self.session.stops.get(sequence_order=1)
        resp = self.client.patch(
            f"/api/sessions/{sid}/stops/{stop1.id}/status/",
            {"status": "delivered"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["stop"]["delivery_status"], "delivered")
        self.assertEqual(resp.json()["current_stop_index"], 2)
        self.assertEqual(resp.json()["session_status"], "in_progress")

        # 3. Mark stop 2 as not_received
        stop2 = self.session.stops.get(sequence_order=2)
        resp = self.client.patch(
            f"/api/sessions/{sid}/stops/{stop2.id}/status/",
            {"status": "not_received"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["stop"]["delivery_status"], "not_received")
        self.assertEqual(resp.json()["current_stop_index"], 3)

        # 4. Skip stop 3 -> route should auto-finish
        stop3 = self.session.stops.get(sequence_order=3)
        resp = self.client.patch(
            f"/api/sessions/{sid}/stops/{stop3.id}/status/",
            {"status": "skipped"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["session_status"], "finished")
        self.assertIsNone(resp.json()["current_stop_index"])

        # 5. Verify session state in DB
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "finished")
        self.assertIsNotNone(self.session.finished_at)

        # 6. Verify via GET session
        resp = self.client.get(f"/api/sessions/{sid}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "finished")

    def test_start_already_started_rejected(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        resp = self.client.patch(f"/api/sessions/{self.session.id}/start/")
        self.assertEqual(resp.status_code, 400)

    def test_start_finished_route_rejected(self):
        self.session.status = "finished"
        self.session.save(update_fields=["status"])
        resp = self.client.patch(f"/api/sessions/{self.session.id}/start/")
        self.assertEqual(resp.status_code, 400)

    def test_start_unoptimized_route_rejected(self):
        self.session.stops.update(sequence_order=None)
        resp = self.client.patch(f"/api/sessions/{self.session.id}/start/")
        self.assertEqual(resp.status_code, 400)

    def test_update_stop_invalid_status_rejected(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        stop = self.session.stops.get(sequence_order=1)
        resp = self.client.patch(
            f"/api/sessions/{self.session.id}/stops/{stop.id}/status/",
            {"status": "exploded"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_nonexistent_stop_rejected(self):
        self.client.patch(f"/api/sessions/{self.session.id}/start/")
        resp = self.client.patch(
            f"/api/sessions/{self.session.id}/stops/999999/status/",
            {"status": "delivered"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_start_nonexistent_session(self):
        resp = self.client.patch("/api/sessions/00000000-0000-0000-0000-000000000000/start/")
        self.assertEqual(resp.status_code, 404)


# ============================================
# E2E: Sharing
# ============================================


class SharingE2E(TestCase):
    """Test share link creation and anonymous access."""

    def setUp(self):
        self.client = _auth_client("share_biker", "biker")
        user = User.objects.get(username="share_biker")
        self.session = DeliverySession.objects.create(owner=user, name="Share Me")
        DeliveryStop.objects.create(
            session=self.session, name="A", lat=47.5, lng=19.08,
            geocode_status="skipped",
        )

    def test_create_and_access_share_link(self):
        # Create share
        resp = self.client.post(f"/api/sessions/{self.session.id}/share/")
        self.assertEqual(resp.status_code, 201)
        share_id = resp.json()["share_id"]

        # Access anonymously
        anon = APIClient()
        resp = anon.get(f"/api/shared/{share_id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["session"]["name"], "Share Me")
        self.assertEqual(len(data["session"]["stops"]), 1)
        self.assertIn("route_geometry", data["session"])

    def test_share_nonexistent_session(self):
        resp = self.client.post("/api/sessions/00000000-0000-0000-0000-000000000000/share/")
        self.assertEqual(resp.status_code, 404)

    def test_shared_route_not_found(self):
        anon = APIClient()
        resp = anon.get("/api/shared/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(resp.status_code, 404)

    def test_multiple_shares_for_same_session(self):
        resp1 = self.client.post(f"/api/sessions/{self.session.id}/share/")
        resp2 = self.client.post(f"/api/sessions/{self.session.id}/share/")
        self.assertNotEqual(resp1.json()["share_id"], resp2.json()["share_id"])
        self.assertEqual(SharedRoute.objects.filter(session=self.session).count(), 2)


# ============================================
# E2E: Live Tracking & Bikers List (planner)
# ============================================


class LiveTrackingE2E(TestCase):
    """Test planner-only endpoints: active sessions and biker list."""

    def setUp(self):
        self.planner = _auth_client("live_planner", "planner")
        self.biker = _auth_client("live_biker", "biker")

        user = User.objects.get(username="live_biker")
        DeliverySession.objects.create(owner=user, name="Active", status="in_progress")
        DeliverySession.objects.create(owner=user, name="Done", status="finished")
        DeliverySession.objects.create(owner=user, name="Waiting", status="not_started")

    def test_active_sessions_only_in_progress(self):
        resp = self.planner.get("/api/sessions/active/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Active")
        self.assertEqual(data[0]["status"], "in_progress")

    def test_active_sessions_response_shape(self):
        resp = self.planner.get("/api/sessions/active/")
        session = resp.json()[0]
        for field in ["id", "name", "owner_name", "owner_id", "status",
                       "started_at", "current_stop_index", "stop_count",
                       "delivered_count", "current_stop_name",
                       "total_duration", "total_distance", "route_geometry", "stops"]:
            self.assertIn(field, session, f"Missing field: {field}")

    def test_active_sessions_biker_rejected(self):
        resp = self.biker.get("/api/sessions/active/")
        self.assertEqual(resp.status_code, 403)

    def test_active_sessions_unauthenticated_rejected(self):
        anon = APIClient()
        resp = anon.get("/api/sessions/active/")
        self.assertEqual(resp.status_code, 401)

    def test_list_bikers(self):
        _auth_client("extra_biker1", "biker")
        _auth_client("extra_biker2", "biker")
        resp = self.planner.get("/api/users/bikers/")
        self.assertEqual(resp.status_code, 200)
        usernames = [u["username"] for u in resp.json()]
        self.assertIn("live_biker", usernames)
        self.assertIn("extra_biker1", usernames)
        self.assertNotIn("live_planner", usernames)

    def test_list_bikers_biker_rejected(self):
        resp = self.biker.get("/api/users/bikers/")
        self.assertEqual(resp.status_code, 403)

    def test_list_bikers_unauthenticated_rejected(self):
        anon = APIClient()
        resp = anon.get("/api/users/bikers/")
        self.assertEqual(resp.status_code, 401)


# ============================================
# E2E: Cross-role Access Control
# ============================================


class CrossRoleAccessE2E(TestCase):
    """Test that bikers can't see other bikers' sessions and planners can."""

    def setUp(self):
        self.biker_a = _auth_client("xrole_a", "biker")
        self.biker_b = _auth_client("xrole_b", "biker")
        self.planner = _auth_client("xrole_planner", "planner")

        user_a = User.objects.get(username="xrole_a")
        self.session_a = DeliverySession.objects.create(owner=user_a, name="A's Route")

    def test_biker_cannot_get_other_bikers_session(self):
        resp = self.biker_b.get(f"/api/sessions/{self.session_a.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_biker_cannot_start_other_bikers_route(self):
        user_a = User.objects.get(username="xrole_a")
        session = _make_optimized_session(user_a)
        resp = self.biker_b.patch(f"/api/sessions/{session.id}/start/")
        self.assertEqual(resp.status_code, 404)

    def test_planner_can_get_any_session(self):
        resp = self.planner.get(f"/api/sessions/{self.session_a.id}/")
        self.assertEqual(resp.status_code, 200)

    def test_unowned_session_accessible_by_any_biker(self):
        session = DeliverySession.objects.create(owner=None, name="Unowned")
        resp = self.biker_b.get(f"/api/sessions/{session.id}/")
        self.assertEqual(resp.status_code, 200)


# ============================================
# E2E: Full Planner Workflow
# ============================================


class PlannerWorkflowE2E(TestCase):
    """Simulate a full planner workflow: upload -> assign -> biker delivers -> planner checks."""

    def setUp(self):
        self.planner = _auth_client("wf_planner", "planner")
        self.biker = _auth_client("wf_biker", "biker")

    def test_full_planner_to_biker_workflow(self):
        biker_user = User.objects.get(username="wf_biker")

        # 1. Planner uploads a route for a biker
        csv = b"name,address,lat,lng\nA,,47.5,19.08\nB,,47.51,19.09\nC,,47.52,19.10\n"
        resp = _upload_csv(self.planner, csv, owner_id=biker_user.id)
        self.assertEqual(resp.status_code, 201)
        session_id = resp.json()["id"]

        # 2. Biker sees it in their session list
        resp = self.biker.get("/api/sessions/")
        self.assertEqual(resp.status_code, 200)
        ids = [s["id"] for s in resp.json()]
        self.assertIn(session_id, ids)

        # 3. Manually set sequence_order (simulating optimization)
        session = DeliverySession.objects.get(id=session_id)
        for i, stop in enumerate(session.stops.all(), 1):
            stop.sequence_order = i
            stop.save(update_fields=["sequence_order"])

        # 4. Biker starts the route
        resp = self.biker.patch(f"/api/sessions/{session_id}/start/")
        self.assertEqual(resp.status_code, 200)

        # 5. Planner sees it as active
        resp = self.planner.get("/api/sessions/active/")
        self.assertEqual(resp.status_code, 200)
        active_ids = [s["id"] for s in resp.json()]
        self.assertIn(session_id, active_ids)

        # 6. Biker delivers all stops
        for stop in session.stops.order_by("sequence_order"):
            self.biker.patch(
                f"/api/sessions/{session_id}/stops/{stop.id}/status/",
                {"status": "delivered"},
            )

        # 7. Route is finished
        session.refresh_from_db()
        self.assertEqual(session.status, "finished")

        # 8. Planner no longer sees it as active
        resp = self.planner.get("/api/sessions/active/")
        active_ids = [s["id"] for s in resp.json()]
        self.assertNotIn(session_id, active_ids)

        # 9. Planner can still see it in full list
        resp = self.planner.get("/api/sessions/")
        ids = [s["id"] for s in resp.json()]
        self.assertIn(session_id, ids)

        # 10. Planner can delete the finished route
        resp = self.planner.delete(f"/api/sessions/{session_id}/delete/")
        self.assertEqual(resp.status_code, 204)
