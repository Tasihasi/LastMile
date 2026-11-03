import re

# Budapest postal codes are 1DDx where DD is the district number (01-23),
# e.g. 1052 -> district 5, 1114 -> district 11.
_BUDAPEST_ZIP_RE = re.compile(r"\b1(\d{2})\d\b")

ROMAN_NUMERALS = [
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "XIII",
    "XIV",
    "XV",
    "XVI",
    "XVII",
    "XVIII",
    "XIX",
    "XX",
    "XXI",
    "XXII",
    "XXIII",
]


def extract_district(raw_address):
    """Extract a Budapest district number (1-23) from an address, or None."""
    if not raw_address:
        return None
    match = _BUDAPEST_ZIP_RE.search(raw_address)
    if not match:
        return None
    district = int(match.group(1))
    if 1 <= district <= 23:
        return district
    return None


_ANY_ZIP_RE = re.compile(r"(?<!\d)[1-9]\d{3}(?!\d)")


def extract_postal_code(raw_address):
    """Best-effort 4-digit Hungarian irányítószám from an address, as a string ("" if none)."""
    if not raw_address:
        return ""
    budapest = extract_zip(raw_address)
    if budapest:
        return str(budapest)
    match = _ANY_ZIP_RE.search(raw_address)
    return match.group(0) if match else ""


def extract_zip(raw_address):
    """Extract the full 4-digit Budapest irányítószám (postal code) from an address, or None.

    Only recognizes codes within a valid district (1001-1230), matching extract_district.
    """
    if not raw_address:
        return None
    match = _BUDAPEST_ZIP_RE.search(raw_address)
    if not match:
        return None
    district = int(match.group(1))
    if 1 <= district <= 23:
        return int(match.group(0))
    return None


def district_label(district):
    """Human-readable label, e.g. 5 -> 'V. kerület'."""
    if district is None or not 1 <= district <= 23:
        return None
    return f"{ROMAN_NUMERALS[district - 1]}. kerület"
