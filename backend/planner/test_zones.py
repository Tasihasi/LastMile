import json
import tempfile
from pathlib import Path

from django.test import TestCase

from . import zones


def _write(cfg):
    path = Path(tempfile.mkdtemp()) / "z.json"
    path.write_text(cfg if isinstance(cfg, str) else json.dumps(cfg), encoding="utf-8")
    return path


class ZonesTests(TestCase):
    def test_a1_bundled_config_valid_and_not_placeholder(self):
        cfg = zones.load()
        zones.validate_config(cfg)
        self.assertFalse(zones.is_placeholder())
        self.assertEqual(len(zones.all_zones()), 16)
        self.assertEqual(sum(len(z["zips"]) for z in zones.all_zones()), 34)

    def test_a1_ac2_wrong_counts_rejected_unless_placeholder(self):
        cfg = {"zones": [{"id": "A", "zips": ["1051"]}]}
        with self.assertRaisesRegex(zones.ZoneConfigError, "16 zones"):
            zones.validate_config(cfg)
        zones.validate_config({**cfg, "_placeholder": True})

    def test_a1_out_of_area_zip_unzoned(self):
        self.assertIsNone(zones.zone_for_zip("1111"))

    def test_a1_ac1_duplicate_zip_rejected(self):
        cfg = {"zones": [{"id": "A", "zips": ["1051"]}, {"id": "B", "zips": ["1051"]}]}
        with self.assertRaisesRegex(zones.ZoneConfigError, "1051"):
            zones.validate_config(zones.load(_write(cfg)))

    def test_a1_ac3_lookup(self):
        self.assertEqual(zones.zone_for_zip("1083"), zones.zone_for_zip("1082"))
        self.assertEqual(zones.zone_for_zip(1082), zones.zone_for_zip("1082"))
        self.assertIsNone(zones.zone_for_zip("9999"))
        self.assertIsNone(zones.zone_for_zip(None))
        self.assertEqual(zones.zips_in_zone(zones.zone_for_zip("1082")), ["1082", "1083"])
        self.assertEqual(zones.zips_in_zone("nope"), [])

    def test_a1_ac5_bad_zip_names_entry(self):
        cfg = {"zones": [{"id": "Z9", "zips": ["2051"]}]}
        with self.assertRaisesRegex(zones.ZoneConfigError, "Z9.*2051"):
            zones.validate_config(cfg)

    def test_a1_ac5_malformed_json(self):
        with self.assertRaises(zones.ZoneConfigError):
            zones.load(_write("{not json"))

    def test_a1_ac5_bad_shapes(self):
        for cfg in (
            [],
            {"zones": "x"},
            {"zones": [1]},
            {"zones": [{"zips": ["1051"]}]},
            {"zones": [{"id": "A", "zips": []}]},
        ):
            with self.assertRaises(zones.ZoneConfigError):
                zones.validate_config(cfg)


class ZoneEditingApiTests(TestCase):
    """Planners manage zones by hand; the lookups used for splitting follow the edits."""

    def setUp(self):
        from rest_framework.test import APIClient

        from .test_e2e_api import _auth_client

        zones.invalidate()
        self.addCleanup(zones.invalidate)
        self.planner = _auth_client("zeditor", "planner")
        self.biker = _auth_client("zbiker2", "biker")
        self.anon = APIClient()

    def test_create_zone_is_used_for_lookup(self):
        resp = self.planner.post("/api/zones/", {"name": "Outer", "zips": ["1111", "1113"]}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["id"], "Z17")
        self.assertEqual(zones.zone_for_zip("1113"), "Z17")
        self.assertEqual(zones.zips_in_zone("Z17"), ["1111", "1113"])

    def test_update_moves_zip_between_zones(self):
        zid = zones.zone_for_zip("1082")
        resp = self.planner.put(f"/api/zones/{zid}/", {"name": "Baross", "zips": ["1082"]}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(zones.zone_for_zip("1083"))
        again = self.planner.post("/api/zones/", {"zips": ["1083"]}, format="json")
        self.assertEqual(again.status_code, 201)

    def test_delete_zone_unzones_its_codes(self):
        zid = zones.zone_for_zip("1051")
        self.assertEqual(self.planner.delete(f"/api/zones/{zid}/").status_code, 204)
        self.assertIsNone(zones.zone_for_zip("1051"))
        self.assertEqual(self.planner.delete(f"/api/zones/{zid}/").status_code, 404)

    def test_rejects_overlap_bad_and_empty_zips(self):
        for zips, needle in (
            (["1082"], "already belongs"),
            (["2051"], "Invalid"),
            ([], "at least one"),
            (["1111", "1111"], "twice"),
        ):
            resp = self.planner.post("/api/zones/", {"zips": zips}, format="json")
            self.assertEqual(resp.status_code, 400, zips)
            self.assertIn(needle, resp.json()["error"])
        self.assertEqual(len(zones.all_zones()), 16)

    def test_planner_only(self):
        zid = zones.zone_for_zip("1051")
        body = {"zips": ["1111"]}
        self.assertEqual(self.anon.post("/api/zones/", body, format="json").status_code, 401)
        self.assertEqual(self.biker.post("/api/zones/", body, format="json").status_code, 403)
        self.assertEqual(self.biker.put(f"/api/zones/{zid}/", body, format="json").status_code, 403)
        self.assertEqual(self.biker.delete(f"/api/zones/{zid}/").status_code, 403)

    def test_edited_zones_drive_allocation_units(self):
        """A manually added zone becomes one planning unit; deleting it splits it back into zips."""
        from types import SimpleNamespace

        from .zone_allocation import zone_units

        stops = [SimpleNamespace(postal_code=z, lat=47.5, lng=19.05) for z in ("1111", "1111", "1113")]
        self.assertEqual(sorted(zone_units(stops)), ["zip:1111", "zip:1113"])
        zid = self.planner.post("/api/zones/", {"name": "XI", "zips": ["1111", "1113"]}, format="json").json()["id"]
        self.assertEqual({k: len(v) for k, v in zone_units(stops).items()}, {zid: 3})
        self.planner.delete(f"/api/zones/{zid}/")
        self.assertEqual(sorted(zone_units(stops)), ["zip:1111", "zip:1113"])
