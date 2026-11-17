import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from . import zones


def _write(cfg):
    path = Path(tempfile.mkdtemp()) / "z.json"
    path.write_text(cfg if isinstance(cfg, str) else json.dumps(cfg), encoding="utf-8")
    return path


class ZonesTests(SimpleTestCase):
    def test_a1_bundled_config_valid_and_not_placeholder(self):
        cfg = zones.load()
        zones.validate_config(cfg)
        self.assertFalse(zones.is_placeholder())
        # Data from the customer sheet: 22 zones / 40 zips (spec said 16/34, see PR notes).
        self.assertEqual(len(zones.all_zones()), 22)
        self.assertEqual(sum(len(z["zips"]) for z in zones.all_zones()), 40)

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
