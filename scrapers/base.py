"""BaseScraper — provides default strategies so most venue scrapers need only URL config.

Extraction strategies, in order of preference:

  1. JSON-LD schema.org/Event blocks on the events page
  2. iCal feed (if declared via `ical_url`)
  3. RSS / Atom feed (if declared via `feed_url`)
  4. Subclass override of `custom_parse(html) -> list[dict]`

Whichever strategy returns non-empty is used. Subclasses only need to set
class attrs; they rarely need to write parsing code.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from icalendar import Calendar
import feedparser

from .utils.http import get
from .utils.event_id import event_id
from .utils.event_type import infer as infer_type
from .utils.dateparse import to_la_iso, now_utc_iso


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
        return asdict(self)


class BaseScraper:
    """Subclass and set class attrs. Call `.run()` to produce a list of Event dicts."""

    venue_id: str = ""
    events_url: str = ""        # Page the site links humans to
    ical_url: Optional[str] = None
    feed_url: Optional[str] = None
    source_label: str = ""       # Short label, usually the bare domain

    def run(self) -> list[dict]:
        strategies: Iterable = (
            self._strategy_jsonld,
            self._strategy_ical,
            self._strategy_feed,
            self._strategy_custom,
        )
        for strat in strategies:
            try:
                events = list(strat())
            except Exception as e:
                print(f"  [{self.venue_id}] strategy {strat.__name__} failed: {e}")
                events = []
            if events:
                return [e.to_dict() for e in events]
        return []

    # ------- Strategies -------

    def _strategy_jsonld(self) -> Iterable[Event]:
        if not self.events_url:
            return
        resp = get(self.events_url)
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

    def _strategy_ical(self) -> Iterable[Event]:
        if not self.ical_url:
            return
        resp = get(self.ical_url)
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

    def _strategy_feed(self) -> Iterable[Event]:
        if not self.feed_url:
            return
        feed = feedparser.parse(self.feed_url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title:
                continue
            desc = (entry.get("summary", "") or entry.get("description", "") or "").strip()
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

    # ------- Conversions -------

    def _event_from_jsonld(self, obj: dict) -> Event:
        title = (obj.get("name") or "").strip()
        desc = (obj.get("description") or "").strip()
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
        desc = str(component.get("description", "")).strip()
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

    @staticmethod
    def _domain(url: str) -> str:
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc
            return host.replace("www.", "")
        except Exception:
            return ""


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
    return "other"
