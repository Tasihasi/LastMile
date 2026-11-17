"""Zone config: which postal codes (irányítószám) belong to which sorting zone.

Data lives in zones.json. If the file is a stand-in, it is
flagged ``"_placeholder": true`` and a warning is logged at startup.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

ZONES_PATH = Path(__file__).with_name("zones.json")
_ZIP_RE = re.compile(r"^1\d{3}$")


EXPECTED_ZONES = 16
EXPECTED_ZIPS = 34


class ZoneConfigError(ValueError):
    """The zone config is malformed."""


def load(path=None):
    """Read and parse a zone config file (default: the bundled zones.json)."""
    path = Path(path) if path else ZONES_PATH
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ZoneConfigError(f"Cannot read zone config {path.name}: {exc}") from exc


def validate_config(config):
    """Raise ZoneConfigError (naming the offending entry) if the config is invalid."""
    if not isinstance(config, dict) or not isinstance(config.get("zones"), list):
        raise ZoneConfigError("Config must be an object with a 'zones' list.")
    seen_ids = set()
    seen_zips = {}
    for index, zone in enumerate(config["zones"]):
        if not isinstance(zone, dict):
            raise ZoneConfigError(f"zones[{index}] must be an object.")
        zone_id = zone.get("id")
        if not isinstance(zone_id, str) or not zone_id:
            raise ZoneConfigError(f"zones[{index}] has no valid 'id'.")
        if zone_id in seen_ids:
            raise ZoneConfigError(f"Duplicate zone id {zone_id!r}.")
        seen_ids.add(zone_id)
        zips = zone.get("zips")
        if not isinstance(zips, list) or not zips:
            raise ZoneConfigError(f"Zone {zone_id!r} needs a non-empty 'zips' list.")
        for z in zips:
            if not isinstance(z, str) or not _ZIP_RE.match(z):
                raise ZoneConfigError(rf"Zone {zone_id!r}: invalid zip {z!r} (expected ^1\d{{3}}$).")
            if z in seen_zips:
                raise ZoneConfigError(f"Zip {z} appears in both {seen_zips[z]!r} and {zone_id!r}.")
            seen_zips[z] = zone_id
    if not config.get("_placeholder") and (len(seen_ids), len(seen_zips)) != (EXPECTED_ZONES, EXPECTED_ZIPS):
        raise ZoneConfigError(
            f"Expected {EXPECTED_ZONES} zones and {EXPECTED_ZIPS} zips, got {len(seen_ids)} and {len(seen_zips)}."
        )


_cache = None


def _config():
    global _cache
    if _cache is None:
        config = load()
        validate_config(config)
        _cache = config
    return _cache


def is_placeholder():
    return bool(_config().get("_placeholder"))


def all_zones():
    return [{"id": z["id"], "name": z.get("name", ""), "zips": list(z["zips"])} for z in _config()["zones"]]


def zone_for_zip(zip_code):
    """Zone id for a postal code (str or int), or None if unknown."""
    zip_code = str(zip_code) if zip_code is not None else ""
    for zone in _config()["zones"]:
        if zip_code in zone["zips"]:
            return zone["id"]
    return None


def zips_in_zone(zone_id):
    """Postal codes of a zone ([] if the zone is unknown)."""
    for zone in _config()["zones"]:
        if zone["id"] == zone_id:
            return list(zone["zips"])
    return []


def warn_if_placeholder():
    if is_placeholder():
        logger.warning("zones.json is a PLACEHOLDER - replace it with the real zone table before go-live.")
