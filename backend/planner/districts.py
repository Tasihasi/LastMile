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


def district_label(district):
    """Human-readable label, e.g. 5 -> 'V. kerület'."""
    if district is None or not 1 <= district <= 23:
        return None
    return f"{ROMAN_NUMERALS[district - 1]}. kerület"
