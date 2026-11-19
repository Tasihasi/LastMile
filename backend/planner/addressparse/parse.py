"""Orchestrates the parser steps; every step records what it did in ``ParseResult.steps``."""

from dataclasses import dataclass, field

from django.conf import settings

from .data import is_budapest_zip, settlement_by_name, settlement_for_zip
from .housenumber import parse_house
from .noise import strip_noise
from .normalize import normalize
from .postal import extract_city, extract_district, extract_zip
from .street import correct_street, split_street, type_of
from .variants import build_variants, format_address


@dataclass
class ParseResult:
    raw: str
    cleaned: str = ""
    parts: dict = field(
        default_factory=lambda: {"zip": "", "city": "", "district": None, "street": "", "house": "", "unit": ""}
    )
    removed: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    variants: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    confidence: float = 0.0

    @property
    def ok(self) -> bool:
        """Enough was understood to try a geocoder: a street, and a zip or a settlement."""
        return bool(self.parts["street"] and (self.parts["zip"] or self.parts["city"]))

    def candidates(self) -> list[str]:
        """Distinct address strings a person could pick from, best first."""
        seen, out = set(), []
        for q in [v.query for v in self.variants] + self.suggestions:
            if q.lower() not in seen:
                seen.add(q.lower())
                out.append(q)
        return out

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "cleaned": self.cleaned,
            "parts": self.parts,
            "removed": self.removed,
            "steps": self.steps,
            "variants": [v.to_dict() for v in self.variants],
            "confidence": round(self.confidence, 2),
        }


def _streets_file() -> str:
    return getattr(settings, "ADDRESS_STREETS_FILE", "") or ""


def parse_address(raw: str) -> ParseResult:
    result = ParseResult(raw=raw or "")
    steps = result.steps

    segments, norm_steps = normalize(raw or "")
    steps += norm_steps
    segments, removed = strip_noise(segments)
    result.removed += removed
    for r in removed:
        steps.append(f"removed {r['kind']}: {r['text']}")

    zip_code, segments, zip_leftover = extract_zip(segments)
    if zip_code:
        steps.append(f"postal code {zip_code}")
    district, segments = extract_district(segments)
    if district:
        steps.append(f"district {district}")
    city, segments = extract_city(segments, zip_leftover, zip_code)

    # Zip and settlement must agree; a zip from the table wins over the typed settlement (steps record it).
    zip_city = settlement_for_zip(zip_code)
    if zip_city is not None:
        typed = settlement_by_name(city) if city else None
        if city and typed is not zip_city and typed is not None:
            steps.append(f"zip {zip_code} belongs to {zip_city.name}, not {city}: zip wins")
        if not city or (typed is not None and typed is not zip_city):
            city = zip_city.name
            steps.append(f"settlement {city} from zip")
    if city and settlement_by_name(city):
        city = settlement_by_name(city).name
    if zip_code and not is_budapest_zip(zip_code) and district:
        district = None
    if city and city != "Budapest":
        district = None

    # Street: first segment with a street type; else the first segment with a digit; else the first.
    street_seg = next((s for s in segments if any(type_of(t) for t in s.split()[1:])), None)
    if street_seg is None:
        street_seg = next((s for s in segments if any(c.isdigit() for c in s)), segments[0] if segments else "")
    for s in segments:
        if s is not street_seg:
            result.removed.append({"kind": "unparsed", "text": s})
            steps.append(f"left out: {s}")

    split = split_street(street_seg) if street_seg else None
    street = house = unit = typed_street = ""
    if split and split.name:
        typed_street = f"{split.name} {split.type}".strip()
        street = typed_street
        corr = correct_street(split.name, split.type, city, district, zip_code, _streets_file())
        if corr.auto and corr.street:
            street = corr.street
            steps.append(f"street corrected: {typed_street} -> {street}")
            if corr.dropped:
                result.removed.append({"kind": "name", "text": " ".join(corr.dropped)})
                steps.append(f"dropped words before the street: {' '.join(corr.dropped)}")
        elif corr.suggestions:
            result.suggestions = [format_address(zip_code, city, district, s, "") for s in corr.suggestions]
            steps.append(f"street suggestions: {', '.join(corr.suggestions)}")
        house, unit = parse_house(split.tail)
        if split.tail and not house:
            steps.append(f"no house number in: {split.tail}")

    result.parts = {"zip": zip_code, "city": city, "district": district, "street": street, "house": house, "unit": unit}
    result.cleaned = format_address(zip_code, city, district, street, house, unit) if street else ""

    conf = 0.2
    conf += 0.2 if zip_code and zip_city is not None else (0.1 if zip_code else 0.0)
    conf += 0.15 if city else 0.0
    conf += 0.2 if street and split and split.type else (0.1 if street else 0.0)
    conf += 0.15 if house else 0.0
    conf -= 0.05 * sum(1 for r in result.removed if r["kind"] == "unparsed")
    if street != typed_street:
        conf -= 0.05
    result.confidence = max(0.0, min(1.0, conf))
    result.variants = build_variants(result.parts, typed_street, result.confidence)
    return result
