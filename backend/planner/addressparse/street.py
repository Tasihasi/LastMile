"""Step 5: street name/type split and fuzzy correction against the street list."""

import re
from dataclasses import dataclass, field

from .data import STREET_TYPES, load_streets
from .fold import damerau_levenshtein, fold, phonetic

_NUMLIKE = re.compile(r"^(?:hrsz\.?|\d{1,6}(?:[-/.]\d{0,6})*[A-Za-z]?\.?)$", re.I)
_GLUED = re.compile(r"^(?P<name>\w{3,}?)(?P<type>utca|u\.)$", re.I)


def type_of(token: str) -> str | None:
    """Canonical street type for a token (``u.`` -> ``utca``), or None."""
    return STREET_TYPES.get(fold(token.rstrip(".")))


def _is_number(token: str) -> bool:
    return bool(_NUMLIKE.match(token))


def _unglue(tokens: list[str]) -> list[str]:
    out = []
    for tok in tokens:
        m = _GLUED.match(tok)
        if m and type_of(tok) is None and len(tok) > 5:
            out += [m.group("name"), m.group("type")]
        else:
            out.append(tok)
    return out


def title_case(name: str) -> str:
    """Capitalise a street name unless it already has mixed case (so the function is idempotent)."""
    words = []
    for word in name.split():
        if word.islower() or word.isupper() and len(word) > 1:
            word = "-".join(p[:1].upper() + p[1:].lower() for p in word.split("-"))
        words.append(word)
    return " ".join(words)


@dataclass
class StreetSplit:
    name: str = ""
    type: str = ""  # canonical, '' when the address had none
    tail: str = ""  # everything after the type (house number, unit)
    dropped: list[str] = field(default_factory=list)  # leading words judged not part of the street


def split_street(segment: str) -> StreetSplit:
    tokens = _unglue(segment.split())
    if not tokens:
        return StreetSplit()
    # English-style "14 Kazinczy utca": a leading number moves behind the street.
    if len(tokens) > 2 and _is_number(tokens[0]) and any(type_of(t) for t in tokens[1:]):
        tokens = tokens[1:] + [tokens[0]]
    type_idx = None
    for i, tok in enumerate(tokens):
        if i > 0 and type_of(tok) and (i + 1 == len(tokens) or _is_number(tokens[i + 1])):
            type_idx = i
    if type_idx is None:
        first = next((i for i, t in enumerate(tokens) if i > 0 and type_of(t)), None)
        if first is not None:
            type_idx = first
    if type_idx is not None:
        return StreetSplit(
            name=title_case(" ".join(tokens[:type_idx])),
            type=type_of(tokens[type_idx]) or "",
            tail=" ".join(tokens[type_idx + 1 :]),
        )
    # No street type written ("Kazinczy 14"): name = words before the first number.
    cut = next((i for i, t in enumerate(tokens) if _is_number(t)), len(tokens))
    return StreetSplit(name=title_case(" ".join(tokens[:cut])), tail=" ".join(tokens[cut:]))


@dataclass
class Correction:
    street: str = ""  # corrected "Name type" ('' when no correction)
    distance: int = 0
    auto: bool = False  # safe to apply silently
    dropped: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def _pool(city: str, district: int | None, zip_code: str, extra_file: str) -> list[str]:
    streets = load_streets(extra_file)
    if city.lower() == "budapest":
        by_district = streets.get("budapest", {})
        if district is None and len(zip_code) == 4 and zip_code[0] == "1":
            district = int(zip_code[1:3])
        if district is not None and str(district) in by_district:
            return by_district[str(district)]
        return sorted({n for names in by_district.values() for n in names})
    return streets.get(fold(city), []) if city else []


def correct_street(
    name: str, stype: str, city: str, district: int | None, zip_code: str, extra_file: str = ""
) -> Correction:
    """Match ``name`` against the street list of the zip/district/settlement.

    Auto-applied only for a unique best match: exact up to accents/phonetics, or edit distance <= 2 with a
    margin of >= 2 over the runner-up, and the same street type. Anything weaker is only suggested.
    """
    pool = _pool(city, district, zip_code, extra_file)
    if not pool or not name:
        return Correction()

    def key_of(full: str) -> tuple[str, str]:
        parts = full.rsplit(" ", 1)
        return phonetic(parts[0]), STREET_TYPES.get(fold(parts[1].rstrip(".")), fold(parts[1])) if len(
            parts
        ) == 2 else ""

    words = name.split()
    # Try the whole name first; then without 1-3 leading words (a recipient name glued to the street).
    for drop in range(0, min(3, len(words) - 1) + 1):
        candidate_name = " ".join(words[drop:])
        key = phonetic(candidate_name)
        scored = []
        for full in pool:
            pkey, ptype = key_of(full)
            if stype and ptype and stype != ptype and STREET_TYPES.get(fold(stype)) != ptype:
                continue
            scored.append((damerau_levenshtein(key, pkey), full))
        scored.sort()
        if not scored:
            continue
        best, second = scored[0], scored[1] if len(scored) > 1 else None
        # Same street listed in several districts: identical names are one candidate.
        while second and second[1] == best[1]:
            scored.pop(1)
            second = scored[1] if len(scored) > 1 else None
        margin_ok = second is None or second[0] - best[0] >= 2
        if drop > 0:
            if best[0] == 0 and margin_ok:
                return Correction(street=best[1], distance=0, auto=True, dropped=words[:drop])
            continue
        if best[0] == 0:
            same = best[1] == f"{name} {stype}".strip()
            return Correction(street="" if same else best[1], distance=0, auto=True)
        if best[0] <= 2 and len(key) >= 5 and margin_ok:
            return Correction(street=best[1], distance=best[0], auto=True)
        near = [full for d, full in scored[:3] if d <= 3]
        if near:
            return Correction(suggestions=near)
    return Correction()
