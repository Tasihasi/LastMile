"""Step 7: ordered geocoder query variants for a parsed address."""

from dataclasses import dataclass, field

from .data import ROMAN_BY_NUMBER
from .housenumber import base_number


@dataclass
class Variant:
    kind: str  # full | as_typed | base_number | no_zip | street_only
    query: str
    params: dict = field(default_factory=dict)  # structured form: street, housenumber, postalcode, city
    confidence: float = 0.5
    auto_accept: bool = True  # street-level variants are never auto-accepted (Must #2)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "query": self.query,
            "params": self.params,
            "confidence": round(self.confidence, 2),
            "auto_accept": self.auto_accept,
        }


def head(zip_code: str, city: str, district: int | None) -> str:
    if zip_code:
        return f"{zip_code} {city}".strip()
    if city.lower() == "budapest" and district:
        return f"{city} {ROMAN_BY_NUMBER[district]}. kerület"
    return city


def format_address(zip_code: str, city: str, district: int | None, street: str, house: str, unit: str = "") -> str:
    street_part = " ".join(p for p in (street, house, unit) if p)
    return ", ".join(p for p in (head(zip_code, city, district), street_part) if p)


def build_variants(parts: dict, typed_street: str, confidence: float) -> list[Variant]:
    zip_code, city, district = parts["zip"], parts["city"], parts["district"]
    street, house = parts["street"], parts["house"]
    if not street:
        return []

    def make(kind, st, hn, zp=zip_code, auto=True, conf=confidence):
        params = {"street": " ".join(p for p in (st, hn) if p), "postalcode": zp, "city": city}
        return Variant(kind, format_address(zp, city, district, st, hn), params, conf, auto)

    out = [make("full", street, house)]
    if typed_street and typed_street != street:
        out.append(make("as_typed", typed_street, house, conf=confidence - 0.1))
    base = base_number(house) if house else ""
    if house and base != house:
        out.append(make("base_number", street, base, conf=confidence - 0.15))
    if zip_code and city:
        out.append(make("no_zip", street, house, zp="", conf=confidence - 0.2))
    out.append(make("street_only", street, "", auto=False, conf=confidence - 0.3))
    seen, unique = set(), []
    for v in out:
        if v.query.lower() not in seen:
            seen.add(v.query.lower())
            v.confidence = max(0.0, min(1.0, v.confidence))
            unique.append(v)
    return unique
