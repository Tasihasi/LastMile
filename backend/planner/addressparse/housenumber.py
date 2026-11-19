"""Step 6: house number and unit (staircase / floor / door)."""

import re

_HRSZ = re.compile(r"^\s*hrsz\.?\s*(?P<n>\d{1,6}(?:/\d{1,4})?)", re.I)
_HOUSE = re.compile(
    r"^\s*(?P<n>\d{1,5})"
    r"(?:\s*-\s*(?P<n2>\d{1,5})(?!\d))?"
    r"(?:\s*/\s*(?P<l>[A-Za-z])(?![A-Za-zÀ-ſ])|(?P<l2>[A-Za-z])(?![A-Za-zÀ-ſ.]))?"
    r"(?:\s*/\s*(?P<sub>\d{1,4})(?!\d))?"
    r"\.?"
)


def parse_house(tail: str) -> tuple[str, str]:
    """Split text after the street into (house number, unit). Either may be ''.

    ``12/A``, ``12A`` -> ``12/A``; ``12-14`` kept; ``12/3`` kept; ``hrsz. 123/4`` -> ``hrsz. 123/4``.
    A letter separated by a space (``12 A lh.``) belongs to the unit (staircase), not the number.
    """
    tail = tail.strip()
    if not tail:
        return "", ""
    m = _HRSZ.match(tail)
    if m:
        return f"hrsz. {m.group('n')}", " ".join(tail[m.end() :].split()).strip(" .,")
    m = _HOUSE.match(tail)
    if not m:
        return "", " ".join(tail.split()).strip(" .,")
    house = m.group("n")
    if m.group("n2"):
        house += f"-{m.group('n2')}"
    letter = m.group("l") or m.group("l2")
    if letter:
        house += f"/{letter.upper()}"
    if m.group("sub"):
        house += f"/{m.group('sub')}"
    return house, " ".join(tail[m.end() :].split()).strip(" .,")


def base_number(house: str) -> str:
    """``12/A`` -> ``12``; ``12-14`` -> ``12``; ``hrsz. 12/3`` unchanged."""
    if house.startswith("hrsz"):
        return house
    m = re.match(r"\d+", house)
    return m.group(0) if m else house
