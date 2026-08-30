"""Text repair — fixes character corruption before anything is published.

The bug this exists for: six Getty events reached the live site reading
"Instante/revelaciÃ³n" and "espaÃ±ol" instead of "revelación" and "español".

That happens when a page's bytes are UTF-8 but something along the way read
them as Latin-1. Every accented character becomes two junk characters ("ó"
becomes "Ã³"). It is mechanically reversible: re-encode the mangled string back
to bytes as Latin-1 and decode it as UTF-8.

The repair is conservative. It only fires when the text contains the telltale
sequences AND the round-trip actually succeeds AND the result contains fewer
suspicious characters than we started with. If any of that fails we return the
original untouched — a wrong "fix" would be worse than the corruption.
"""
from __future__ import annotations

import re
import unicodedata

# The signature of UTF-8-read-as-Latin-1. "Ã" or "Â" followed by a continuation
# byte, or the "â€" sequence that mangled smart quotes and dashes produce.
# Any UTF-8 lead byte (\xc2-\xf4) followed by a continuation byte (\x80-\xbf),
# read as if it were Latin-1. Covers "Ã³" (ó), "Ã±" (ñ) and "â\x80\x99" (a
# curly apostrophe) alike — the narrower [ÃÂ] class missed that last one.
_MOJIBAKE_SIGNATURE = re.compile(r"[\xc2-\xf4][\x80-\xbf]")

# Characters that should essentially never appear in a venue's event title.
_SUSPICIOUS = re.compile(r"[\xc2-\xf4][\x80-\xbf]|[Ã\ufffd]")


def looks_mojibaked(s: str) -> bool:
    """True if the string carries the signature of a bad decode."""
    return bool(s) and bool(_MOJIBAKE_SIGNATURE.search(s))


def fix_mojibake(s: str) -> str:
    """Repair UTF-8-read-as-Latin-1 text. Returns the input unchanged if unsure.

    Applied repeatedly (some sources double-encode), but at most three passes so
    a pathological string can't loop.
    """
    if not s or not looks_mojibaked(s):
        return s
    current = s
    for _ in range(3):
        try:
            candidate = current.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        # Only accept the repair if it genuinely reduced the damage.
        if len(_SUSPICIOUS.findall(candidate)) >= len(_SUSPICIOUS.findall(current)):
            break
        current = candidate
        if not looks_mojibaked(current):
            break
    return current


def normalise(s: str) -> str:
    """Full cleanup for any text heading for publication.

    1. Repair a bad decode if there is one.
    2. Normalise Unicode so 'é' written two different ways compares equal.
    3. Replace non-breaking and zero-width spaces with ordinary ones.
    4. Collapse runs of whitespace.
    """
    if not s:
        return ""
    s = fix_mojibake(s)
    s = unicodedata.normalize("NFC", s)
    s = s.replace(" ", " ").replace("​", "").replace("﻿", "")
    return re.sub(r"\s+", " ", s).strip()


def title_key(s: str) -> str:
    """A comparison key for 'is this the same event title?'

    Lowercased, accent-stripped, punctuation-flattened. Used by the recurring
    detector so "Queerchata: Intro to Salsa" and "Queerchata — Intro to Salsa "
    are recognised as the same series.
    """
    s = normalise(s).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()
