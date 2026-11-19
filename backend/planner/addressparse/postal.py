"""Steps 3-4: postal code, Budapest district and settlement."""

import re

from .data import BUDAPEST, ROMAN, STREET_TYPES, settlement_by_name, zip_is_known
from .fold import fold

_ZIP_TOKEN = re.compile(r"(?<![\d/\-.])(?:H[- ]?)?(\d{4})(?!\d|[/\-]\d)")
_DISTRICT_AFTER_CITY = re.compile(r"(?i:budapest|bp)\.?\s*,?\s*(?P<r>[IVX]{1,5})\b\.?(?:\s*ker(?:ület|\.|ulet)?\b\.?)?")
_DISTRICT_ROMAN_KER = re.compile(r"(?<![\w])(?P<r>[IVX]{1,5})\.?\s*ker(?:ület|ulet|\.)?(?![\w])", re.I)
_DISTRICT_ARABIC_KER = re.compile(r"(?<!\d)(?P<n>\d{1,2})\.?\s*ker(?:ület|ulet|\.)?(?![\w])", re.I)


def _last_word_is_type(before: str) -> bool:
    words = before.rstrip(" .").split()
    return bool(words) and fold(words[-1].rstrip(".")) in STREET_TYPES


def extract_zip(segments: list[str]) -> tuple[str, list[str], str]:
    """Pick the postal code. Returns (zip or '', segments without it, leftover text of its segment).

    A 4-digit run is a zip when it leads a segment or is followed by a settlement, or is in the zip table;
    it is never a zip when it directly follows a street type (then it is a house number).
    """
    best = None  # (score, seg_index, match)
    for si, seg in enumerate(segments):
        for m in _ZIP_TOKEN.finditer(seg):
            code = m.group(1)
            if code[0] == "0" or _last_word_is_type(seg[: m.start()]):
                continue
            after = seg[m.end() :].strip(" ,.")
            score = 0
            if not seg[: m.start()].strip(" ,."):
                score += 2  # leads its segment
            first_after = fold(" ".join(after.split()[:2]))
            if after and (settlement_by_name(first_after) or settlement_by_name(first_after.split(" ")[0])):
                score += 2
            if zip_is_known(code):
                score += 2
            if m.group(0)[0] == "H":
                score += 1
            if score >= 2 and (best is None or score > best[0]):
                best = (score, si, m)
    if best is None:
        return "", segments, ""
    _, si, m = best
    seg = segments[si]
    rest = (seg[: m.start()] + " " + seg[m.end() :]).strip(" ,.")
    rest = " ".join(rest.split())
    out = list(segments)
    out[si] = rest
    return m.group(1), [s for s in out if s], rest


def extract_district(segments: list[str]) -> tuple[int | None, list[str]]:
    """Budapest district from ``XIII. ker.``, ``13. kerület`` or ``Budapest VII.``."""
    for si, seg in enumerate(segments):
        for pattern, kind in (
            (_DISTRICT_AFTER_CITY, "roman_city"),
            (_DISTRICT_ROMAN_KER, "roman"),
            (_DISTRICT_ARABIC_KER, "arabic"),
        ):
            m = pattern.search(seg)
            if not m:
                continue
            number = int(m.group("n")) if kind == "arabic" else ROMAN.get(m.group("r").upper())
            if not number or not 1 <= number <= 23:
                continue
            if kind == "roman_city":
                # keep the word "Budapest"; drop only the numeral
                city_word = re.match(r"(?i:budapest|bp)", seg[m.start() :]).group(0)
                replacement = city_word
            else:
                replacement = ""
            new = (seg[: m.start()] + replacement + " " + seg[m.end() :]).strip(" ,.")
            out = list(segments)
            out[si] = " ".join(new.split())
            return number, [s for s in out if s]
    return None, segments


def extract_city(segments: list[str], zip_leftover: str, zip_code: str):
    """Find the settlement. Returns (city name or '', segments without it).

    Order: a segment that is exactly a known settlement, then a known settlement at the start/end of a
    longer segment, then the leftover of the zip's own segment (``2143 Kistarcsa`` -> ``Kistarcsa``).
    """
    for si, seg in enumerate(segments):
        s = settlement_by_name(seg)
        if s:
            return s.name, segments[:si] + segments[si + 1 :]
    for si, seg in enumerate(segments):
        words = seg.split()
        for n in (3, 2, 1):
            if len(words) > n:
                head = settlement_by_name(" ".join(words[:n]).rstrip(".,"))
                if head:
                    new = " ".join(words[n:])
                    return head.name, segments[:si] + [new] + segments[si + 1 :]
                tail = settlement_by_name(" ".join(words[-n:]).rstrip(".,"))
                if tail:
                    new = " ".join(words[:-n])
                    return tail.name, segments[:si] + [new] + segments[si + 1 :]
    # Unknown settlement written next to the zip: "2143 Kistarcsa, Fő utca 3".
    if (
        zip_code
        and zip_leftover
        and not any(c.isdigit() for c in zip_leftover)
        and not any(fold(w.rstrip(".")) in STREET_TYPES for w in zip_leftover.split())
        and zip_leftover in segments
    ):
        idx = segments.index(zip_leftover)
        name = zip_leftover.title() if zip_leftover.islower() else zip_leftover
        return name, segments[:idx] + segments[idx + 1 :]
    return "", segments


__all__ = ["BUDAPEST", "extract_city", "extract_district", "extract_zip"]
