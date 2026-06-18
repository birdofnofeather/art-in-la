"""MAK Center for Art and Architecture — Squarespace events JSON API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://www.makcenter.org"


def _ms_to_iso(ms) -> str | None:
    if not ms:
        return None
    try:
        dt = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


def _ms_to_date(ms) -> str | None:
    """Bare YYYY-MM-DD (LA wall date) for date-only / multi-day exhibitions."""
    if not ms:
        return None
    try:
        # Squarespace stores the wall date at ~01:00 UTC; the UTC calendar day is it.
        dt = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
        return dt.date().isoformat()
    except Exception:
        return None


class Scraper(BaseScraper):
    venue_id = "mak_center"
    events_url = f"{BASE}/events"
    source_label = "makcenter.org"
    drop_exhibitions = False

    def _strategy_custom(self) -> Iterable[Event]:
        # Timed events live in the /events collection; current exhibitions (which
        # run for months and are date-only) live in the separate /exhibitions one.
        yield from self._scrape_collection(f"{BASE}/events", exhibition=False)
        yield from self._scrape_collection(f"{BASE}/exhibitions", exhibition=True)

    def _scrape_collection(self, url: str, exhibition: bool) -> Iterable[Event]:
        resp = get(f"{url}?format=json")
        if not resp or not resp.ok:
            return
        try:
            data = resp.json()
        except Exception:
            return
        for item in data.get("upcoming", []):
            title = (item.get("title") or "").strip()
            if not title:
                continue
            if exhibition:
                start = _ms_to_date(item.get("startDate"))
                end = _ms_to_date(item.get("endDate"))
                all_day = True
            else:
                start = _ms_to_iso(item.get("startDate"))
                end = _ms_to_iso(item.get("endDate"))
                all_day = False
            full_url = item.get("fullUrl", "")
            url_abs = BASE + full_url if full_url.startswith("/") else full_url
            image = item.get("assetUrl") or None
            desc = (item.get("excerpt") or "").strip()

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type="exhibition" if exhibition else infer_type(title, desc),
                start=start,
                end=end,
                all_day=all_day,
                url=url_abs,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])
