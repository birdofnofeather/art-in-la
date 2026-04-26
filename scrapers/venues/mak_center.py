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


class Scraper(BaseScraper):
    venue_id = "mak_center"
    events_url = f"{BASE}/events"
    source_label = "makcenter.org"
    drop_exhibitions = False

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(f"{self.events_url}?format=json")
        if not resp or not resp.ok:
            return
        try:
            data = resp.json()
        except Exception:
            return
        items = data.get("upcoming", [])
        for item in items:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            start = _ms_to_iso(item.get("startDate"))
            end = _ms_to_iso(item.get("endDate"))
            full_url = item.get("fullUrl", "")
            url = BASE + full_url if full_url.startswith("/") else full_url
            image = item.get("assetUrl") or None
            desc = (item.get("excerpt") or "").strip()

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type=infer_type(title, desc),
                start=start,
                end=end,
                all_day=False,
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])
