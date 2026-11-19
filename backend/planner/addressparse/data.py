"""Bundled reference data: settlements, street types, Budapest street seed.

Seed tables, deliberately small and explicit. ``SETTLEMENTS`` lists the larger Hungarian towns with a zip
range and centre; ``load_streets`` merges the Budapest seed with an optional file built from the OSM Hungary
extract (``settings.ADDRESS_STREETS_FILE``, see ``manage.py build_street_index``).
"""

import json
from functools import lru_cache
from pathlib import Path

from .fold import fold


class Settlement:
    __slots__ = ("name", "zip_lo", "zip_hi", "lat", "lng", "radius_km", "key")

    def __init__(self, name, zip_lo, zip_hi, lat, lng, radius_km):
        self.name, self.zip_lo, self.zip_hi = name, zip_lo, zip_hi
        self.lat, self.lng, self.radius_km = lat, lng, radius_km
        self.key = fold(name)


# name, zip_lo, zip_hi, lat, lng, radius_km (radius = how far a hit may be from the centre and still be "in town")
_SETTLEMENTS = [
    ("Budapest", 1011, 1239, 47.4979, 19.0402, 20.0),
    ("Szentendre", 2000, 2000, 47.6694, 19.0756, 9.0),
    ("Pomáz", 2013, 2013, 47.6383, 19.0267, 8.0),
    ("Budakalász", 2011, 2011, 47.6103, 19.0453, 6.0),
    ("Szigetszentmiklós", 2310, 2318, 47.3431, 19.0422, 10.0),
    ("Érd", 2030, 2038, 47.3733, 18.9189, 10.0),
    ("Diósd", 2049, 2049, 47.4055, 18.9439, 6.0),
    ("Budaörs", 2040, 2040, 47.4619, 18.9533, 7.0),
    ("Törökbálint", 2045, 2045, 47.4296, 18.9091, 6.0),
    ("Biatorbágy", 2051, 2053, 47.4703, 18.8236, 8.0),
    ("Budakeszi", 2092, 2092, 47.5097, 18.9272, 7.0),
    ("Solymár", 2083, 2083, 47.5894, 18.9272, 6.0),
    ("Pilisvörösvár", 2085, 2085, 47.6153, 18.9136, 7.0),
    ("Gödöllő", 2100, 2100, 47.5972, 19.3550, 9.0),
    ("Dunakeszi", 2120, 2120, 47.6361, 19.1383, 8.0),
    ("Fót", 2151, 2151, 47.6167, 19.1900, 7.0),
    ("Göd", 2131, 2131, 47.6914, 19.1347, 8.0),
    ("Vác", 2600, 2600, 47.7761, 19.1336, 9.0),
    ("Vecsés", 2220, 2220, 47.4067, 19.2653, 6.0),
    ("Üllő", 2225, 2225, 47.3925, 19.3489, 6.0),
    ("Gyömrő", 2230, 2230, 47.4297, 19.3956, 7.0),
    ("Maglód", 2234, 2234, 47.4503, 19.3544, 6.0),
    ("Gyál", 2360, 2360, 47.3828, 19.2194, 6.0),
    ("Dunaharaszti", 2330, 2330, 47.3556, 19.0903, 6.0),
    ("Százhalombatta", 2440, 2440, 47.3153, 18.9111, 8.0),
    ("Cegléd", 2700, 2700, 47.1731, 19.7994, 9.0),
    ("Tatabánya", 2800, 2840, 47.5692, 18.4047, 11.0),
    ("Dunaújváros", 2400, 2400, 46.9619, 18.9356, 9.0),
    ("Székesfehérvár", 8000, 8006, 47.1860, 18.4221, 12.0),
    ("Veszprém", 8200, 8230, 47.0933, 17.9115, 11.0),
    ("Győr", 9021, 9030, 47.6875, 17.6504, 12.0),
    ("Mosonmagyaróvár", 9200, 9200, 47.8686, 17.2708, 9.0),
    ("Sopron", 9400, 9400, 47.6817, 16.5845, 10.0),
    ("Szombathely", 9700, 9700, 47.2307, 16.6218, 11.0),
    ("Zalaegerszeg", 8900, 8900, 46.8417, 16.8416, 10.0),
    ("Nagykanizsa", 8800, 8800, 46.4590, 16.9897, 9.0),
    ("Kaposvár", 7400, 7400, 46.3594, 17.7968, 10.0),
    ("Pécs", 7621, 7636, 46.0727, 18.2323, 12.0),
    ("Szekszárd", 7100, 7100, 46.3474, 18.7062, 9.0),
    ("Baja", 6500, 6500, 46.1811, 18.9544, 9.0),
    ("Kecskemét", 6000, 6044, 46.8964, 19.6897, 12.0),
    ("Szeged", 6720, 6729, 46.2530, 20.1414, 12.0),
    ("Hódmezővásárhely", 6800, 6800, 46.4181, 20.3300, 10.0),
    ("Békéscsaba", 5600, 5600, 46.6736, 21.0877, 10.0),
    ("Szolnok", 5000, 5008, 47.1621, 20.1825, 10.0),
    ("Debrecen", 4024, 4034, 47.5316, 21.6273, 14.0),
    ("Nyíregyháza", 4400, 4400, 47.9554, 21.7167, 12.0),
    ("Miskolc", 3510, 3534, 48.1035, 20.7784, 13.0),
    ("Eger", 3300, 3300, 47.9025, 20.3772, 9.0),
    ("Salgótarján", 3100, 3100, 48.0936, 19.8003, 9.0),
]

SETTLEMENTS = [Settlement(*row) for row in _SETTLEMENTS]
_BY_KEY = {s.key: s for s in SETTLEMENTS}
BUDAPEST = _BY_KEY["budapest"]


def settlement_by_name(text: str):
    """Settlement for a name; ``Bp.``/``Bp`` mean Budapest. None if unknown."""
    key = fold(text)
    if key in ("bp", "budapest"):
        return BUDAPEST
    return _BY_KEY.get(key)


def is_budapest_zip(zip_code: str) -> bool:
    """Budapest zips are 1DDx, DD = district 01-23 (1011-1239)."""
    if not zip_code or len(zip_code) != 4 or not zip_code.isdigit() or zip_code[0] != "1":
        return False
    return 1 <= int(zip_code[1:3]) <= 23 and int(zip_code) >= 1011


def settlement_for_zip(zip_code: str):
    """The settlement whose zip range contains ``zip_code`` (Budapest only for valid district zips)."""
    if not zip_code or not zip_code.isdigit() or len(zip_code) != 4:
        return None
    if is_budapest_zip(zip_code):
        return BUDAPEST
    z = int(zip_code)
    for s in SETTLEMENTS:
        if s is not BUDAPEST and s.zip_lo <= z <= s.zip_hi:
            return s
    return None


def zip_is_known(zip_code: str) -> bool:
    return settlement_for_zip(zip_code) is not None


# Street-type lexicon: folded spelling -> canonical word (matching is on folded tokens).
STREET_TYPES = {
    "u": "utca",
    "utca": "utca",
    "utc": "utca",
    "utcaja": "utcája",
    "ut": "út",
    "utja": "útja",
    "krt": "körút",
    "korut": "körút",
    "korutja": "körútja",
    "ter": "tér",
    "koz": "köz",
    "setany": "sétány",
    "stny": "sétány",
    "fasor": "fasor",
    "rakpart": "rakpart",
    "rkp": "rakpart",
    "dulo": "dűlő",
    "ltp": "lakótelep",
    "lakotelep": "lakótelep",
    "telep": "telep",
    "park": "park",
    "sor": "sor",
    "liget": "liget",
    "hid": "híd",
    "udvar": "udvar",
    "major": "major",
    "hatarut": "határút",
    "sugarut": "sugárút",
    "sgt": "sugárút",
    "korter": "körtér",
    "lepcso": "lépcső",
    "sikator": "sikátor",
    "atjaro": "átjáró",
}

# Roman numerals for Budapest districts.
ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12,
    "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20, "XXI": 21,
    "XXII": 22, "XXIII": 23,
}  # fmt: skip
ROMAN_BY_NUMBER = {v: k for k, v in ROMAN.items()}

_STREETS_SEED = Path(__file__).parent / "streets_hu.json"


@lru_cache(maxsize=4)
def load_streets(extra_file: str = "") -> dict:
    """``{"budapest": {"7": [names]}, "<folded settlement>": [names]}`` merged with an optional OSM-built file."""
    data = json.loads(_STREETS_SEED.read_text(encoding="utf-8"))
    if extra_file:
        path = Path(extra_file)
        if path.is_file():
            extra = json.loads(path.read_text(encoding="utf-8"))
            for key, value in extra.items():
                if isinstance(value, dict):
                    bucket = data.setdefault(key, {})
                    for k, names in value.items():
                        bucket[k] = sorted(set(bucket.get(k, [])) | set(names))
                else:
                    data[key] = sorted(set(data.get(key, [])) | set(value))
    return data
