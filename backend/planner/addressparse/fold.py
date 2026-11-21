"""Text folding helpers: diacritics, Hungarian phonetics, Damerau-Levenshtein distance."""

import unicodedata


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(c for c in decomposed if unicodedata.category(c) != "Mn"))


def fold(text: str) -> str:
    """Lower-case, accent-free, punctuation-free key (``Kazinczy u.`` -> ``kazinczy u``)."""
    base = strip_accents(text.lower())
    return " ".join("".join(c if c.isalnum() else " " for c in base).split())


# Hungarian spellings that sound alike; folded so "Hunyadi"/"Hunjadi" or "Széll"/"Szél" meet.
_PHONETIC = [
    ("ly", "j"),
    ("dzs", "j"),
    ("ccs", "cs"),
    ("ssz", "sz"),
    ("zzs", "zs"),
    ("tty", "ty"),
    ("ggy", "gy"),
    ("nny", "ny"),
    ("ll", "l"),
    ("tt", "t"),
    ("nn", "n"),
    ("ss", "s"),
    ("rr", "r"),
    ("kk", "k"),
    ("pp", "p"),
    ("gg", "g"),
    ("bb", "b"),
    ("dd", "d"),
    ("mm", "m"),
    ("ff", "f"),
    ("zz", "z"),
    ("y", "i"),
    ("w", "v"),
    ("x", "ks"),
    ("q", "k"),
]


def phonetic(text: str) -> str:
    key = fold(text).replace(" ", "")
    for a, b in _PHONETIC:
        key = key.replace(a, b)
    return key


def damerau_levenshtein(a: str, b: str) -> int:
    """Optimal-string-alignment distance (insert, delete, substitute, adjacent transposition)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if not la or not lb:
        return la or lb
    prev2: list[int] = []
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[lb]
