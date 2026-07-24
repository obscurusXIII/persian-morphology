"""Conservative Unicode and orthographic normalization for Persian input."""

from __future__ import annotations

import re
import unicodedata

ZWNJ = "\u200c"

_CHARACTER_MAP = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ـ": None,
        "\ufeff": None,
        "\u200b": None,
        "\u200d": None,
        "\u200e": None,
        "\u200f": None,
    }
)

_DIACRITICS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_WHITESPACE = re.compile(r"\s+")
_MULTIPLE_ZWNJ = re.compile(f"{ZWNJ}+")
_SPACE_AROUND_ZWNJ = re.compile(rf"\s*{ZWNJ}\s*")
_STRAY_ZWNJ = re.compile(rf"(?:^{ZWNJ}|{ZWNJ}$|(?<=\s){ZWNJ}|{ZWNJ}(?=\s))")

# This is intentionally narrow. It fixes an explicitly separated verbal mi-/nemi-
# but does not split arbitrary strings beginning with می, which could be lexical words.
_SEPARATED_MI = re.compile(r"(?<!\S)(ن?می)\s+(?=[آ-ی])")

# Formal present-perfect clitics are written with a half-space after De.  This
# does not reinterpret a synthetic past such as رفتم as a perfect.
_SEPARATED_PERFECT_CLITIC = re.compile(r"(?<!\S)([آ-ی\u200c]+ه)\s+(ام|ای|ایم|اید|اند)(?!\S)")


def normalize(text: str, *, remove_diacritics: bool = True, join_verbal_mi: bool = True) -> str:
    """Return a canonical Persian spelling suitable for FST lookup.

    The function is deterministic and idempotent. It does not perform dictionary
    correction or informal-to-formal replacement.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    result = unicodedata.normalize("NFC", text).translate(_CHARACTER_MAP)
    if remove_diacritics:
        result = _DIACRITICS.sub("", result)

    result = _SPACE_AROUND_ZWNJ.sub(ZWNJ, result)
    result = _MULTIPLE_ZWNJ.sub(ZWNJ, result)
    result = _WHITESPACE.sub(" ", result).strip()

    if join_verbal_mi:
        result = _SEPARATED_MI.sub(rf"\1{ZWNJ}", result)

    result = _SEPARATED_PERFECT_CLITIC.sub(rf"\1{ZWNJ}\2", result)

    result = _STRAY_ZWNJ.sub("", result)
    return unicodedata.normalize("NFC", result)
