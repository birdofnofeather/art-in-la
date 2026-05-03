"""BaseScraper — provides default strategies so most venue scrapers need only URL config.

Extraction strategies, tried in order until one returns events:

  1. WordPress Tribe Events REST API (auto-detected at /wp-json/tribe/events/v1/events)
  2. iCal feed (if declared via `ical_url`, or auto-detected at /events/?ical=1)
  3. JSON-LD schema.org/Event blocks on the events page
  4. RSS / Atom feed (if declared via `feed_url`)
  5. Subclass override of `custom_parse(html, base_url) -> list[Event]`

After collection, every event passes through `_postprocess`:

  - Multi-day date ranges (>36h) are KEPT and re-typed as `exhibition`. They
    surface in the Exhibitions tab.
  - Anything explicitly typed `exhibition` is also kept.
  - Openings are NEVER synthesized from exhibition start times — they are
    captured only when the source explicitly lists an opening reception as its
    own event (e.g. a Tribe REST entry, a JSON-LD Event titled "Opening …").
    This avoids inventing public opening dates for shows that don't have one.

Subclasses normally just set class attrs:

    class Scraper(BaseScraper):
        venue_id = "foo"
        events_url = "https://foo.com/events"
        # ical_url = "..."        # optional, otherwise auto-detected
        # feed_url = "..."        # optional
        # wp_root  = "..."        # optional, otherwise inferred from events_url
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from icalendar import Calendar
import feedparser

from .utils.http import get
from .utils.event_id import event_id
from .utils.event_type import infer as infer_type
from .utils.dateparse import to_la_iso, now_utc_iso

LA_TZ_OFFSET = "-07:00"  # PDT; PST is -08:00. Daily scrape near-LA time, fine for now.

# Multi-day events whose duration exceeds this are treated as exhibitions
# (date ranges) rather than one-off events.
EXHIBITION_THRESHOLD = timedelta(hours=36)

_HTML_ENTITY = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&nbsp;": " ",
    "&quot;": '"', "&#39;": "'", "&apos;": "'", "&mdash;": "—",
    "&ndash;": "–", "&lsquo;": "'", "&rsquo;": "'",
    "&ldquo;": "“", "&rdquo;": "”",
}
_ENTITY_RE = re.compile(r"&#?[a-zA-Z0-9]+;")


def _strip_html(text: str) -> str:
    """Remove HTML tags, decode entities, collapse whitespace."""
    if not text:
        return ""
    # Remove tags (including self-closing and multi-line)
    text = re.sub(r"<[^>]+>", " ", text, flags=re.DOTALL)
    # Decode named + numeric entities
    def replace_entity(m):
        s = m.group(0)
        if s in _HTML_ENTITY:
            return _HTML_ENTITY[s]
        # Numeric: &#NNN; or &#xHH;
        try:
            if s.startswith("&#x") or s.startswith("&#X"):
                return chr(int(s[3:-1], 16))
            if s.startswith("&#"):
                return chr(int(s[2:-1]))
        except (ValueError, OverflowError):
            pass
        return s
    text = _ENTITY_RE.sub(replace_entity, text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Event:
    id: str
    venue_id: str
    title: str
    description: str
    event_type: str
    start: Optional[str]
    end: Optional[str]
    all_day: bool
    url: Optional[str]
    image: Optional[str]
    artists: list = field(default_factory=list)
    location_override: Optional[str] = None
    source: str = ""
    scraped_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        # Scrapers may pass datetime objects instead of ISO strings — normalise here.
        for key in ("start", "end", "scraped_at"):
            val = d.get(key)
            if isinstance(val, datetime):
                d[key] = val.isoformat()
        return d


class BaseScraper:
    """Subclass and set class attrs. Call `.run()` to produce a list of Event dicts."""

    venue_id: str = ""
    events_url: str = ""        # Page the site links humans to
    ical_url: Optional[str] = None
    feed_url: Optional[str] = None
    wp_root: Optional[str] = None      # Override the WP REST root (defaults to events_url's origin)
    eventbrite_url: Optional[str] = None  # Public Eventbrite organizer page (events embedded as JSON-LD)
    source_label: str = ""       # Short label, usually the bare domain

    # Subclass can opt out of post-processing if they really do want raw output.
    drop_exhibitions: bool = True

    def run(self) -> list[dict]:
        strategies = (
            ("wp_tribe",   self._strategy_wp_tribe),
            ("ical",       self._strategy_ical),
            ("jsonld",     self._strategy_jsonld),
            ("eventbrite", self._strategy_eventbrite),
            ("feed",       self._strategy_feed),
            ("custom",     self._strategy_custom),
        )
        events: list[Event] = []
        for name, strat in strategies:
            try:
                got = list(strat())
            except Exception as e:
                print(f"  [{self.venue_id}] strategy {name} failed: {e}")
                got = []
            if got:
                print(f"  [{self.venue_id}] strategy {name}: {len(got)} raw events")
                events = got
                break
        if not events:
            print(f"  [{self.venue_id}] no strategy returned events")
            return []

        if self.drop_exhibitions:
            events = self._postprocess(events)
            n_exh = sum(1 for e in events if e.event_type == "exhibition")
            n_one = len(events) - n_exh
            print(f"  [{self.venue_id}] after reshape: {n_one} one-off + {n_exh} exhibition events")
        return [e.to_dict() for e in events]

    # ------- Strategies -------

    def _strategy_wp_tribe(self) -> Iterable[Event]:
        """WordPress with The Events Calendar plugin exposes a clean JSON REST API
        listing only one-off events (not exhibitions). Try it first because it's
        the cleanest source available on roughly half the venues we scrape.
        """
        if not self.events_url:
            return
        root = self.wp_root or self._origin(self.events_url)
        url = root.rstrip("/") + "/wp-json/tribe/events/v1/events?per_page=50"
        resp = get(url)
        if not resp or resp.status_code != 200:
            return
        try:
            data = resp.json()
        except Exception:
            return
        items = data.get("events") or []
        if not isinstance(items, list):
            return
        for it in items:
            title = (it.get("title") or "").strip()
            if not title:
                continue
            desc_html = it.get("description") or ""
            desc = _strip_html(desc_html)
            start = self._tribe_to_la_iso(it.get("start_date"))
            end = self._tribe_to_la_iso(it.get("end_date"))
            url_e = it.get("url")
            image = (it.get("image") or {}).get("url") if isinstance(it.get("image"), dict) else None
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day=False,
                url=url_e,
                image=image,
                source=self.source_label or self._domain(self.events_url),
                scraped_at=now_utc_iso(),
            )

    def _strategy_ical(self) -> Iterable[Event]:
        # Auto-detect Tribe Events ical: /events/?ical=1 — works on many WP venues.
        url = self.ical_url
        if not url and self.events_url:
            guess = self.events_url.rstrip("/") + "/?ical=1"
            resp = get(guess)
            if resp and resp.status_code == 200 and "BEGIN:VCALENDAR" in resp.text[:200]:
                url = guess
        if not url:
            return
        resp = get(url)
        if not resp or not resp.ok:
            return
        try:
            cal = Calendar.from_ical(resp.text)
        except Exception:
            return
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            yield self._event_from_ical(component)

    def _strategy_eventbrite(self) -> Iterable[Event]:
        """Public Eventbrite organizer pages embed each event as JSON-LD; this
        is the cleanest source for venues that publish there instead of (or in
        addition to) their own site. Set `eventbrite_url` on the subclass.
        """
        if not self.eventbrite_url:
            return
        yield from self._jsonld_events_from_url(self.eventbrite_url)

    def _strategy_jsonld(self) -> Iterable[Event]:
        if not self.events_url:
            return
        yield from self._jsonld_events_from_url(self.events_url)

    def _jsonld_events_from_url(self, url: str) -> Iterable[Event]:
        resp = get(url)
        if not resp or not resp.ok:
            return
        soup = BeautifulSoup(resp.text, "lxml")
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            payload = script.string or script.text
            if not payload:
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for obj in _flatten_jsonld(data):
                if _is_event(obj):
                    yield self._event_from_jsonld(obj)

    def _strategy_feed(self) -> Iterable[Event]:
        if not self.feed_url:
            return
        feed = feedparser.parse(self.feed_url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title:
                continue
            desc = _strip_html(entry.get("summary", "") or entry.get("description", "") or "")
            start = to_la_iso(entry.get("published") or entry.get("updated"))
            link = entry.get("link")
            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=None,
                all_day=False,
                url=link,
                image=None,
                source=self.source_label or self._domain(self.events_url),
                scraped_at=now_utc_iso(),
            )

    def _strategy_custom(self) -> Iterable[Event]:
        if not self.events_url:
            return
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        yield from self.custom_parse(resp.text, resp.url)

    # Override this in subclasses for per-site HTML parsing.
    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        return []

    # ------- Post-processing -------

    def _postprocess(self, events: list[Event]) -> list[Event]:
        """Re-type long ranges as exhibitions; pair with synthesized openings."""
        out: list[Event] = []
        for ev in events:
            kept = self._reshape(ev)
            if kept is None:
                continue
            if isinstance(kept, list):
                out.extend(kept)
            else:
                out.append(kept)
        return out

    def _reshape(self, ev: Event):
        """Returns Event or None.
           - Event: keep as-is (or re-typed as exhibition).
           - None: drop entirely.

        Multi-day non-fair events get re-typed to `exhibition` so the front-end
        can route them to the Exhibitions tab. We do NOT invent opening events;
        those only exist when the source explicitly lists them.
        """
        if ev.event_type == "exhibition":
            return ev
        dur = self._duration(ev)
        if dur is not None and dur > EXHIBITION_THRESHOLD:
            if ev.event_type in {"fair"}:
                # Fairs can legitimately span days — keep as fair.
                return ev
            return replace(
                ev,
                id=event_id(self.venue_id, ev.start, ev.title + "::exh"),
                event_type="exhibition",
            )
        return ev

    def _duration(self, ev: Event):
        s = _parse_iso(ev.start)
        e = _parse_iso(ev.end)
        if not s or not e:
            return None
        return e - s

    # ------- Conversions -------

    def _event_from_jsonld(self, obj: dict) -> Event:
        title = (obj.get("name") or "").strip()
        desc = _strip_html(obj.get("description") or "")
        start = to_la_iso(obj.get("startDate"))
        end = to_la_iso(obj.get("endDate"))
        url = obj.get("url")
        if isinstance(url, list):
            url = url[0] if url else None
        image = obj.get("image")
        if isinstance(image, dict):
            image = image.get("url")
        if isinstance(image, list):
            image = image[0] if image else None
            if isinstance(image, dict):
                image = image.get("url")

        location = obj.get("location")
        loc_override = None
        if isinstance(location, dict):
            loc_override = location.get("name")
        elif isinstance(location, str):
            loc_override = location

        performers = obj.get("performer") or obj.get("performers") or []
        if isinstance(performers, dict):
            performers = [performers]
        artists = []
        for p in performers or []:
            if isinstance(p, dict) and p.get("name"):
                artists.append(p["name"])
            elif isinstance(p, str):
                artists.append(p)

        return Event(
            id=event_id(self.venue_id, start, title),
            venue_id=self.venue_id,
            title=title,
            description=desc[:800],
            event_type=infer_type(title, desc, default=_jsonld_type_hint(obj)),
            start=start,
            end=end,
            all_day=False,
            url=url,
            image=image,
            artists=artists,
            location_override=loc_override,
            source=self.source_label or self._domain(self.events_url),
            scraped_at=now_utc_iso(),
        )

    def _event_from_ical(self, component) -> Event:
        title = str(component.get("summary", "")).strip()
        desc = _strip_html(str(component.get("description", "")))
        dtstart = component.get("dtstart")
        dtend = component.get("dtend")
        start_raw = dtstart.dt if dtstart else None
        end_raw = dtend.dt if dtend else None
        all_day = hasattr(start_raw, "year") and not hasattr(start_raw, "hour")
        start = to_la_iso(start_raw, all_day=all_day)
        end = to_la_iso(end_raw, all_day=all_day) if end_raw else None
        url = str(component.get("url") or "") or None
        location = str(component.get("location") or "") or None
        return Event(
            id=event_id(self.venue_id, start, title),
            venue_id=self.venue_id,
            title=title,
            description=desc[:800],
            event_type=infer_type(title, desc),
            start=start,
            end=end,
            all_day=all_day,
            url=url,
            image=None,
            location_override=location,
            source=self.source_label or self._domain(self.events_url),
            scraped_at=now_utc_iso(),
        )

    # ------- Helpers -------

    @staticmethod
    def _domain(url: str) -> str:
        try:
            host = urlparse(url).netloc
            return host.replace("www.", "")
        except Exception:
            return ""

    @staticmethod
    def _origin(url: str) -> str:
        try:
            p = urlparse(url)
            return f"{p.scheme}://{p.netloc}"
        except Exception:
            return ""

    @staticmethod
    def _tribe_to_la_iso(s: Optional[str]) -> Optional[str]:
        """Tribe REST returns 'YYYY-MM-DD HH:MM:SS' in venue-local time (no offset)."""
        if not s:
            return None
        s = s.strip()
        if "T" not in s:
            s = s.replace(" ", "T", 1)
        # If it doesn't carry a tz offset, attach LA time.
        if not (s.endswith("Z") or re.search(r"[+-]\d\d:?\d\d$", s)):
            s = s + LA_TZ_OFFSET
        return s


# -------- ISO datetime helpers --------

def _parse_iso(s: Optional[str]):
    if not s:
        return None
    try:
        # Python 3.11+ accepts most ISO8601 forms; '+00:00' or 'Z' both fine.
        s2 = s.replace("Z", "+00:00") if s.endswith("Z") else s
        return datetime.fromisoformat(s2)
    except Exception:
        return None


# -------- JSON-LD helpers --------

def _flatten_jsonld(data) -> Iterable[dict]:
    """Yield every dict node; JSON-LD can be a list, a @graph, or nested."""
    if isinstance(data, list):
        for item in data:
            yield from _flatten_jsonld(item)
    elif isinstance(data, dict):
        yield data
        if "@graph" in data:
            yield from _flatten_jsonld(data["@graph"])


def _is_event(obj: dict) -> bool:
    t = obj.get("@type")
    if isinstance(t, list):
        return any(_type_matches(x) for x in t)
    return _type_matches(t)


EVENT_TYPES = {
    "event", "exhibitionevent", "exhibition", "visualartsevent",
    "theaterevent", "screeningevent", "educationevent", "socialevent",
    "festival", "businessevent",
}


def _type_matches(t) -> bool:
    if not t:
        return False
    return str(t).lower().lstrip("schema:") in EVENT_TYPES


def _jsonld_type_hint(obj: dict) -> str:
    t = obj.get("@type", "")
    if isinstance(t, list):
        t = t[0] if t else ""
    tl = str(t).lower()
    if "screen" in tl:
        return "screening"
    if "educat" in tl:
        return "workshop"
    if "exhibition" in tl:
        return "exhibition"
    if "festival" in tl:
        return "fair"
    return "other"
