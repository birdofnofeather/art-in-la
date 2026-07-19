"""Free / price extraction.

Two inputs feed a venue's cost signal:
  * JSON-LD `offers` (price / lowPrice / highPrice / isAccessibleForFree)
  * The Events-Calendar REST `cost` string ("Free", "$10", "$10 – $25")
  * Free-text keyword fallback on the title + description

Produces two optional fields:
  * is_free  -> True / False / None   (NEVER guessed False from absence)
  * price_text -> short display string ("Free", "$10", "$10–$25") or None
"""
from __future__ import annotations

import re

_FREE_PHRASE = re.compile(
    r"\b(free\s+admission|free\s+event|free\s+to\s+attend|free\s+and\s+open|"
    r"no\s+charge|admission\s+is\s+free|free\s+with\s+rsvp|rsvp[^.]{0,24}\bfree\b)\b",
    re.I,
)
_FREE_WORD = re.compile(r"\bfree\b", re.I)
_PAID_HINT = re.compile(r"\bfree\s+(?:members?|for\s+members?|parking|wifi)\b", re.I)
_PRICE = re.compile(r"\$\s?(\d{1,4}(?:\.\d{2})?)")


def _money(x: float) -> str:
    return f"${int(x)}" if float(x).is_integer() else f"${x:.2f}"


def _fmt_range(prices: list[float]) -> str | None:
    if not prices:
        return None
    lo, hi = min(prices), max(prices)
    return _money(lo) if lo == hi else f"{_money(lo)}–{_money(hi)}"


def parse_offers(offers) -> tuple[bool | None, str | None]:
    """From a JSON-LD `offers` (dict | list | None) -> (is_free, price_text)."""
    if not offers:
        return None, None
    if isinstance(offers, dict):
        offers = [offers]
    free = None
    prices: list[float] = []
    for o in offers:
        if not isinstance(o, dict):
            continue
        acc = o.get("isAccessibleForFree")
        if isinstance(acc, str):
            acc = acc.strip().lower() in ("true", "1", "yes")
        if acc is True:
            free = True
        for k in ("price", "lowPrice", "highPrice"):
            v = o.get(k)
            if v in (None, ""):
                continue
            try:
                prices.append(float(str(v).replace("$", "").replace(",", "").strip()))
            except (ValueError, TypeError):
                pass
    price_text = _fmt_range(prices)
    if prices:
        lo, hi = min(prices), max(prices)
        if hi == 0:
            free = True
            price_text = None
        elif lo == 0 and free is None:
            free = False  # some tiers free, some paid -> not a "free" event
    if free and not price_text:
        price_text = "Free"
    return free, price_text


def parse_cost(cost) -> tuple[bool | None, str | None]:
    """From a REST `cost` string ('Free', '$10', '$10 - $25') -> (is_free, price_text)."""
    if cost in (None, ""):
        return None, None
    c = str(cost).strip()
    if not c:
        return None, None
    low = c.lower()
    if low in ("0", "free", "$0", "0.00", "$0.00"):
        return True, "Free"
    nums = [float(m) for m in _PRICE.findall(c)]
    if nums:
        if max(nums) == 0:
            return True, "Free"
        return None, _fmt_range(nums)
    return None, None


def infer_from_text(title: str, description: str = "") -> tuple[bool | None, str | None]:
    """Keyword fallback -> (is_free, price_text). Only ever returns is_free True."""
    text = f"{title or ''} \n {description or ''}"
    if _FREE_PHRASE.search(text) and not _PAID_HINT.search(text):
        return True, "Free"
    m = _PRICE.findall(text)
    if m:
        return None, _fmt_range([float(x) for x in m])
    if _FREE_WORD.search(text) and not _PAID_HINT.search(text):
        return True, "Free"
    return None, None


def resolve(title, description, is_free=None, price_text=None, offers=None, cost=None):
    """Combine explicit signals (offers/cost) then fall back to text keywords."""
    if is_free is None and price_text is None and offers is not None:
        is_free, price_text = parse_offers(offers)
    if is_free is None and price_text is None and cost is not None:
        is_free, price_text = parse_cost(cost)
    if is_free is None and price_text is None:
        is_free, price_text = infer_from_text(title, description)
    if is_free is None and price_text == "Free":
        is_free = True
    return is_free, price_text
