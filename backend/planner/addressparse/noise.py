"""Step 2: remove things that are not part of an address (and keep them in ``removed``).

Safety rule: a digit run directly after a street type is a house number and is never removed.
"""

import re

from .data import STREET_TYPES
from .fold import fold

_MONTHS = (
    "január|február|március|április|május|június|július|augusztus|szeptember|október|november|december|"
    "jan|feb|márc|ápr|máj|jún|júl|aug|szept|okt|nov|dec"
)

# (kind, regex). Whole-shape matches only.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("url", re.compile(r"(?:https?://|www\.)\S+", re.I)),
    ("date", re.compile(r"(?<!\d)(?:19|20)\d{2}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*\d{1,2}\.?(?!\d)")),
    ("date", re.compile(r"(?<!\d)\d{1,2}\s*[.\-/]\s*\d{1,2}\s*[.\-/]\s*(?:19|20)\d{2}\.?(?!\d)")),
    ("date", re.compile(rf"(?<!\d)(?:19|20)\d{{2}}\.?\s*(?:{_MONTHS})\.?\s*\d{{1,2}}\.?", re.I)),
    ("date", re.compile(r"(?<!\d)(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?!\d)")),
    ("phone", re.compile(r"(?<![\d])(?:\+|00)36[\s\-/.]*\(?\d{1,2}\)?[\s\-/.]*\d{3}[\s\-/.]*\d{3,4}(?!\d)")),
    ("phone", re.compile(r"(?<![\d])\(?06\)?[\s\-/.]*\(?\d{1,2}\)?[\s\-/.]*\d{3}[\s\-/.]*\d{3,4}(?!\d)")),
    ("phone", re.compile(r"(?<![\d])(?:20|30|31|50|70)\s*[/\-]\s*\d{3}[\s\-]?\d{3,4}(?!\d)")),
    ("phone", re.compile(r"(?<![\d])1\s*/\s*\d{3}[\s\-]?\d{4}(?!\d)")),
    ("tracking", re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}\d{9}[A-Z]{2}(?![A-Za-z0-9])")),
    ("tracking", re.compile(r"(?<![A-Za-z0-9])1Z[0-9A-Z]{16}(?![A-Za-z0-9])")),
    ("tracking", re.compile(r"(?<!\d)\d{10,}(?!\d)")),
]

# Notes that carry a value: the keyword and one value token go (kapukód: 1234, tel: ...).
_VALUE_NOTE = re.compile(
    r"(?<!\w)(?:kapu\s*kód\w*|kapukód\w*|tel(?:efon(?:szám)?)?\.?(?=\s*[:+(\d])|mobil\b|e-?mail\b)"
    r"\s*[:\-]?\s*[\d+()/\-.]*",
    re.I,
)
# Birth-date markers: only the keyword goes (the date itself is removed by the date patterns).
_BIRTH_NOTE = re.compile(r"(?<!\w)(?:szül\w*\.?|született\b|szd\.)\s*[:\-]?", re.I)
# Free-text delivery notes: from the keyword to the end of the segment.
_FREE_NOTE = re.compile(
    r"(?<!\w)(?:csengő\w*|csengo\w*|hívj\w*|hívni\b|hívás\w*|megjegyzés\w*|megj\.|portás\w*|postaláda\w*|"
    r"átvevő\w*|kérem\b|kérjük\b|délután\b|délelőtt\b|reggel\b|este\b)",
    re.I,
)
_TITLE = re.compile(r"(?<!\w)(?:dr|özv|ifj|id|prof|ifjabb|idősebb)\.", re.I)


def _is_type(token: str) -> bool:
    return fold(token.rstrip(".")) in STREET_TYPES


def _after_street_type(text: str, start: int) -> bool:
    """True when the characters before ``start`` end with a street type word (so a number there is a house number)."""
    before = text[:start].rstrip(" .")
    if not before:
        return False
    last = before.split()[-1]
    return _is_type(last)


def _has_type(text: str) -> bool:
    return any(_is_type(t) for t in text.split())


def _strip_patterns(segment: str, removed: list[dict]) -> str:
    for kind, pattern in _PATTERNS:
        pos = 0
        while True:
            m = pattern.search(segment, pos)
            if not m:
                break
            if _after_street_type(segment, m.start()):
                pos = m.end()
                continue
            removed.append({"kind": kind, "text": m.group(0).strip()})
            segment = (segment[: m.start()] + " " + segment[m.end() :]).strip()
            pos = 0
    return " ".join(segment.split())


def _strip_notes(segment: str, removed: list[dict]) -> str:
    while True:
        m = _VALUE_NOTE.search(segment) or _BIRTH_NOTE.search(segment)
        if m:
            removed.append({"kind": "note", "text": m.group(0).strip()})
            segment = " ".join((segment[: m.start()] + " " + segment[m.end() :]).split())
            continue
        m = _FREE_NOTE.search(segment)
        if not m:
            return segment
        rest = segment[m.end() :]
        if m.start() == 0 or _has_type(rest):
            # keep what follows: it may still hold the address (e.g. "Hívjon! 1075 Budapest")
            word = re.match(r"\S+", segment[m.start() :]).group(0)
            removed.append({"kind": "note", "text": word})
            segment = " ".join((segment[: m.start()] + " " + segment[m.start() + len(word) :]).split())
        else:
            removed.append({"kind": "note", "text": segment[m.start() :].strip()})
            segment = segment[: m.start()].strip()


def strip_noise(segments: list[str]) -> tuple[list[str], list[dict]]:
    removed: list[dict] = []
    out: list[str] = []
    for seg in segments:
        seg = _strip_patterns(seg, removed)
        seg = _strip_notes(seg, removed)
        # A title on a segment that has no street type and no digit is a recipient name: drop it whole.
        if _TITLE.search(seg) and not _has_type(seg) and not any(c.isdigit() for c in seg):
            removed.append({"kind": "name", "text": seg})
            continue
        seg = seg.strip(" -:.!?")
        if any(c.isalnum() for c in seg):
            out.append(seg)
    return out, removed
