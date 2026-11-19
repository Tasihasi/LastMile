"""Rule-based Hungarian address parser (no AI, no statistical model).

``parse_address(raw)`` turns a messy delivery address into a :class:`ParseResult`: cleaned text,
structured parts, what was removed as noise, an audit trail and ordered geocoder query variants.
Everything is plain regexes, lookup tables and edit distance, so a result is explainable and testable.
"""

from .parse import ParseResult, parse_address
from .variants import Variant

__all__ = ["ParseResult", "Variant", "parse_address"]
