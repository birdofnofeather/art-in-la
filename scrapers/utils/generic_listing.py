"""Generic listing extractor — reads an events/exhibitions page with no feed.

Most small venue sites have no machine-readable feed, but nearly all of them
render their listing the same way: a repeated "card" holding a title (a heading
or a link) next to a human-readable date ("Nov 14, 2026", "Oct 5 – Jan 12",
"Saturday, December 6 · 7 PM"). This module finds those cards without knowing
anything about the site:

  1. Every text fragment that contains a date is located.
  2. For each, we climb to the smallest ancestor that also holds a title
     (heading or link) but NOT a second, different card's date — that ancestor
     is the card.
  3. Title, URL, image, date range and time are read from the card.

It is deliberately conservative: anything that does not look like a listing
card (nav links, "Read more", footers, dates in the past beyond a grace window,
titles that are just dates) is discarded. A page that yields nothing simply
returns [] and the next strategy (the LLM tier, when enabled) gets its turn.

No network here except the single page fetch; everything is pure and testable
against saved HTML (see scrapers/tests/test_generic_listing.py).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MON = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|"
        r"Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?")
_DOW = r"(?:(?:Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun)[a-z]*\.?,?\s+)?"
# "Nov 14, 2026" / "November 14" / "14 November 2026" / "11/14/2026"
def _md(n):
    return (_DOW + r"(?P<m%d>" % n + _MON + r")\s+(?P<d%d>\d{1,2})(?:st|nd|rd|th)?"
            r"(?:,?\s+(?P<y%d>20\d\d))?" % (n, n))


def _dm(n):
    return (_DOW + r"(?P<d%d>\d{1,2})\s+(?P<m%d>" % (n, n) + _MON + r")"
            r"(?:,?\s+(?P<y%d>20\d\d))?" % n)


_SEP = r"\s*(?:–|—|-|to|through|thru|until)\s*"
_ONE = re.compile(_md(1), re.I)
_ONE_DM = re.compile(_dm(1), re.I)
_ONE_NUM = re.compile(r"\b(?P<nm1>\d{1,2})/(?P<nd1>\d{1,2})/(?P<ny1>(?:20)?\d\d)\b")
# A range whose second half may omit the month: "Oct 5 – 19, 2026"
_RANGE = re.compile(
    _md(1) + _SEP + r"(?:(?P<m2>" + _MON + r")\s+)?(?P<d2>\d{1,2})(?:st|nd|rd|th)?"
    # the second number must not be an HOUR ("Dec 6 - 7pm", "Dec 12 - 8:00 PM")
    r"(?!\s*(?::\d|[ap]\.?m\b|o'?clock))(?:,?\s+(?P<y2>20\d\d))?",
    re.I,
)
_TIME = re.compile(r"\b(?P<h>\d{1,2})(?::(?P<mi>\d{2}))?\s*(?P<ap>a\.?m\.?|p\.?m\.?)", re.I)
_NOON = re.compile(r"\bnoon\b", re.I)

_JUNK_TITLE = re.compile(
    r"^(read more|learn more|more info(?:rmation)?|details|tickets?|buy tickets|"
    r"register|rsvp|view (?:event|details|all|more)|see (?:all|more)|more|info|"
    r"book now|reserve|sign up|subscribe|donate|share|calendar|add to calendar|"
    r"upcoming|past|events?|exhibitions?|programs?|home|menu|search|next|previous|"
    r"time (?:&|and) location|what'?s new|what'?s on|on view|now on view|current|"
    r"load more|show more|filter|today|this week|all events|image|photo|about the event|"
    r"\W*)$",
    re.I,
)
_SKIP_TAGS = ("script", "style", "noscript", "nav", "header", "footer", "form", "svg", "iframe")

# Past items more than this many days old are ignored (a listing often shows
# a few recent past events below the upcoming ones).
PAST_GRACE_DAYS = 2


def _month(s: str) -> Optional[int]:
    return MONTHS.get(s.lower().rstrip(".")[:3])


def _infer_year(m: int, d: int, today: date) -> Optional[date]:
    """No year printed: take the occurrence nearest to (but not long before) today."""
    for y in (today.year, today.year + 1):
        try:
            cand = date(y, m, d)
        except ValueError:
            return None
        if cand >= today - timedelta(days=60):
            return cand
    return None


def _mk(y, m, d, today) -> Optional[date]:
    try:
        if y:
            y = int(y)
            if y < 100:
                y += 2000
            return date(y, m, d)
        return _infer_year(m, d, today)
    except (ValueError, TypeError):
        return None


def parse_dates(text: str, today: date) -> Optional[tuple[date, Optional[date], Optional[str]]]:
    """Return (start, end, time 'HH:MM') for the first date expression in text."""
    start = end = None
    rm = _RANGE.search(text)
    if rm:
        m1 = _month(rm.group("m1")); d1 = int(rm.group("d1"))
        m2 = _month(rm.group("m2")) if rm.group("m2") else m1
        d2 = int(rm.group("d2"))
        y2 = rm.group("y2") or rm.group("y1")
        y1 = rm.group("y1")              # only a year printed on the START
        if m1 and m2:
            end = _mk(y2, m2, d2, today)
            if y1:
                start = _mk(y1, m1, d1, today)
            elif end:
                # "Nov 20 – Jan 10, 2027": start year may be the year before.
                start = _mk(end.year, m1, d1, today)
                if start and start > end:
                    start = _mk(end.year - 1, m1, d1, today)
            if start and end and (end < start or (end - start).days > 400):
                start, end = None, None        # implausible: fall back to single date
    if not start:
        for rx, mk, dk, yk in ((_ONE, "m1", "d1", "y1"), (_ONE_DM, "m1", "d1", "y1")):
            mm = rx.search(text)
            if mm:
                mo = _month(mm.group(mk))
                if mo:
                    start = _mk(mm.group(yk), mo, int(mm.group(dk)), today)
                    if start:
                        break
    if not start:
        mm = _ONE_NUM.search(text)
        if mm:
            start = _mk(mm.group("ny1"), int(mm.group("nm1")), int(mm.group("nd1")), today)
    if not start:
        return None
    tm = None
    # Look for the time only in what is left once the dates are removed, so a
    # day number ("Dec 12 - 8 PM") is never read as an hour.
    text = _ONE_NUM.sub(" ", _ONE_DM.sub(" ", _ONE.sub(" ", _RANGE.sub(" ", text))))
    # "7-9pm" / "7:30 – 9 PM": the START hour takes the meridiem of the end.
    span = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(?:–|—|-|to)\s*\d{1,2}(?::\d{2})?\s*([ap])\.?m\b", text, re.I)
    t = _TIME.search(text)
    if span and (not t or span.start() <= t.start()):
        h = int(span.group(1)); mi = int(span.group(2) or 0)
        if 1 <= h <= 12 and mi < 60:
            pm = span.group(3).lower() == "p"
            if pm and h != 12 and h < 12:
                # "11-1pm" starts in the morning; otherwise same meridiem as the end
                end_h = int(re.search(r"(?:–|—|-|to)\s*(\d{1,2})", span.group(0)).group(1))
                if not (h > end_h and end_h != 12):
                    h += 12
            if not pm and h == 12:
                h = 0
            return start, end, f"{h:02d}:{mi:02d}"
    if t:
        h = int(t.group("h")); mi = int(t.group("mi") or 0)
        if 1 <= h <= 12 and mi < 60:
            if t.group("ap").lower().startswith("p") and h != 12:
                h += 12
            if t.group("ap").lower().startswith("a") and h == 12:
                h = 0
            tm = f"{h:02d}:{mi:02d}"
    elif _NOON.search(text):
        tm = "12:00"
    return start, end, tm


def _has_date(text: str) -> bool:
    return bool(_ONE.search(text) or _ONE_DM.search(text) or _ONE_NUM.search(text))


_PREFIX = re.compile(r"^(?:read|learn|find out|see) more(?: about)?\s*[:\-–]?\s*", re.I)


def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip(" \t\n|·•–—-:")
    return _PREFIX.sub("", s).strip()


def _title_of(card: Tag) -> tuple[Optional[str], Optional[str]]:
    """(title, href) — prefer a heading, else the most title-like link."""
    for h in card.find_all(["h1", "h2", "h3", "h4", "h5"]):
        t = _clean(h.get_text(" "))
        if 3 <= len(t) <= 160 and not _JUNK_TITLE.match(t) and not _is_only_date(t):
            a = h.find("a", href=True) or h.find_parent("a", href=True)
            if not a:
                a = next((x for x in card.find_all("a", href=True)
                          if not x.get("href", "").startswith(("#", "mailto:", "tel:"))), None)
            return t, (a.get("href") if a else None)
    best = None
    for a in card.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        t = _clean(a.get_text(" "))
        if not (4 <= len(t) <= 160) or _JUNK_TITLE.match(t) or _is_only_date(t):
            continue
        if best is None or len(t) > len(best[0]):
            best = (t, href)
    if best:
        return best
    # Class-named title elements ("event-title", "card__title") without heading tags.
    for el in card.find_all(class_=re.compile(r"title|name|heading", re.I)):
        t = _clean(el.get_text(" "))
        if 3 <= len(t) <= 160 and not _JUNK_TITLE.match(t) and not _is_only_date(t):
            a = card.find("a", href=True)
            return t, (a.get("href") if a else None)
    return None, None


_DATEWORDS = re.compile(r"\b(through|thru|until|till|on view|opens?|closes?|from|to|and|"
                        r"daily|ongoing|now|extended)\b", re.I)


def _is_only_date(t: str) -> bool:
    stripped = _TIME.sub("", _RANGE.sub("", _ONE.sub("", _ONE_DM.sub("", _ONE_NUM.sub("", t)))))
    stripped = _DATEWORDS.sub("", stripped)
    return len(re.sub(r"[\W\d_]+", "", stripped)) < 3


def _image_of(card: Tag, base: str) -> Optional[str]:
    img = card.find("img")
    if not img:
        return None
    src = img.get("src") or img.get("data-src") or ""
    if not src and img.get("srcset"):
        src = img["srcset"].split(",")[0].split()[0]
    if not src or src.startswith("data:"):
        return None
    return urljoin(base, src)


def extract(html: str, base_url: str, today: Optional[date] = None,
            max_items: int = 80) -> list[dict]:
    """Return a list of {title,url,start,end,time,image,text} dicts."""
    today = today or date.today()
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all(_SKIP_TAGS):
        t.decompose()
    root = soup.find("main") or soup.body or soup

    # 1. date-bearing text fragments
    anchors: list[Tag] = []
    for s in root.find_all(string=True):
        if not isinstance(s, NavigableString):
            continue
        txt = str(s)
        if len(txt) > 400 or not _has_date(txt):
            continue
        if s.parent is not None:
            anchors.append(s.parent)
    # Dates split across sibling spans ("Nov" <span>14</span>) are caught by
    # also testing small elements' combined text.
    for el in root.find_all(["time", "span", "div", "p", "li"]):
        if el in anchors:
            continue
        txt = el.get_text(" ", strip=True)
        if 5 <= len(txt) <= 60 and _has_date(txt) and not any(
                c in anchors for c in el.find_all(True)):
            anchors.append(el)

    out: list[dict] = []
    seen_cards: set[int] = set()
    seen_keys: set[tuple] = set()
    for el in anchors:
        card = el
        title = href = None
        for _ in range(7):
            parent = card.parent
            if parent is None or parent is root.parent:
                break
            card = parent
            text = card.get_text(" ", strip=True)
            if len(text) > 1500:
                break
            title, href = _title_of(card)
            if title:
                break
        if not title or id(card) in seen_cards:
            continue
        text = _clean(card.get_text(" "))
        # A "card" that contains several unrelated dated items is the whole
        # listing, not one card — skip rather than mis-pair title and date.
        n_dates = len({m.group(0).lower() for m in _ONE.finditer(text)})
        if n_dates > 3 or len(text) > 1500:
            continue
        seen_cards.add(id(card))
        date_text = el.get_text(" ", strip=True)
        got = parse_dates(date_text, today) or parse_dates(text, today)
        if not got:
            continue
        start, end, tm = got
        # Every year printed in the card or its link is in the past → this is
        # an old listing whose year we would otherwise have guessed wrong.
        yrs = [int(y) for y in re.findall(r"(?<!\d)(20\d\d)(?!\d)", text + " " + (href or ""))]
        if yrs and max(yrs) < today.year:
            continue
        # The year was NOT printed with the date and we inferred "next year".
        # Listing pages often show recent PAST events without a year (a summer
        # series seen in November), which inference would push into next
        # year. Only trust an inferred next-year date if it is near (<7
        # months) and nothing in the card names an earlier year.
        year_printed = bool(re.search(r"(?<!\d)20\d\d(?!\d)", date_text))
        if not year_printed and start.year > today.year:
            if (start - today).days > 210 or (yrs and min(yrs) <= today.year and max(yrs) <= today.year):
                continue
        last_day = end or start
        if last_day < today - timedelta(days=PAST_GRACE_DAYS):
            continue
        if start > today + timedelta(days=550):
            continue
        # "Intro to Bandsaw Box, Saturday, December 5th | 10 am" — a date
        # glued onto the title. Cut the title where the date begins.
        m = re.search(r"[,|·–—-]\s*" + _DOW + "(?:" + _MON + r")\s+\d", title)
        if m and m.start() >= 8:
            title = title[: m.start()].strip()
        key = (title.lower(), start)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        out.append({
            "title": title,
            "url": urljoin(base_url, href) if href else None,
            "start": start, "end": end, "time": tm,
            "image": _image_of(card, base_url),
            "text": text[:600],
        })
        if len(out) >= max_items:
            break
    return out
