import io
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import DeliverySession, DeliveryStop
from .parsers import parse_csv, parse_file, parse_txt, parse_xml


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
        content = b"name\taddress\tlatklng\nShop A\tMain St\t\t\n"
        # Fix: actual tab-delimited with correct headers
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
        # 3 have coordinates, 9 have addresses
        with_coords = [r for r in rows if r["lat"] is not None]
        self.assertEqual(len(with_coords), 3)

    def test_sample_txt(self):
        with open(self._sample_path("sample.txt"), "rb") as f:
            rows = parse_txt(f)
        self.assertGreaterEqual(len(rows), 1)

    def test_sample_xml(self):
        with open(self._sample_path("sample.xml"), "rb") as f:
            rows = parse_xml(f)
        self.assertGreaterEqual(len(rows), 1)


class UploadAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

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


class SessionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.session = DeliverySession.objects.create()
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
        # Only 1 located stop -- should fail
        DeliveryStop.objects.filter(session=self.session, name="Shop A").update(lat=None, lng=None)
        response = self.client.post(f"/api/sessions/{self.session.id}/optimize/")
        self.assertEqual(response.status_code, 400)
