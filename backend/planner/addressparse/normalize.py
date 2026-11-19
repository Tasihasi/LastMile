"""Step 1: Unicode/encoding clean-up and segmentation."""

import re
import unicodedata

_LEGACY = {"õ": "ő", "û": "ű", "Õ": "Ő", "Û": "Ű"}  # ISO-8859-1/Windows-1250 mix-ups
_MOJIBAKE_HINT = re.compile("[ÃÂÅ][\u0080-ÿŒœŠšŸŽžƒˆ˜–—‘-„†-•…‰‹›€™]")
_DROP_CATEGORIES = {"Cc", "Cf", "Co", "Cs", "So", "Sk"}
_SEPARATORS = re.compile(r"[,;|\n\r\t]+")
_DASHES = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-"})


def fix_mojibake(text: str) -> str:
    """UTF-8 bytes read as cp1252/latin-1 (``KazinczyÃ¼`` -> ``Kazinczyü``), then legacy ``õ``/``û``."""
    if _MOJIBAKE_HINT.search(text):
        for enc in ("cp1252", "latin-1"):
            try:
                fixed = text.encode(enc).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            text = fixed
            break
    return "".join(_LEGACY.get(c, c) for c in text)


def normalize(raw: str) -> tuple[list[str], list[str]]:
    """Return (segments, steps). Segments are the comma/semicolon/pipe/newline separated pieces, trimmed."""
    steps: list[str] = []
    text = unicodedata.normalize("NFC", raw or "")
    fixed = fix_mojibake(text)
    if fixed != text:
        steps.append("fixed encoding / legacy accents")
    text = fixed.translate(_DASHES)
    # Keep newlines/tabs (they separate segments); drop other control chars, emoji and symbols.
    cleaned = "".join(c if c in "\n\r\t" or unicodedata.category(c) not in _DROP_CATEGORIES else " " for c in text)
    if cleaned != text:
        steps.append("removed control characters / emoji")
    text = cleaned
    segments = [" ".join(part.split()) for part in _SEPARATORS.split(text)]
    return [s for s in segments if s], steps
