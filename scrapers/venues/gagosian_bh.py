"""Gagosian Beverly Hills scraper.

Fetches the Beverly Hills location page for the list of exhibitions,
then hits the Gagosian REST API (gagosian.com/api/gallery/exhibitions/<slug>/)
for start/end dates per show.
"""
from __future__ import annotations
import json
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://gagosian.com"


class Scraper(BaseScraper):
    venue_id = "gagosian_bh"
    events_url = f"{BASE}/locations/beverly-hills/"
    source_label = "gagosian.com"
    drop_exhibitions: bool = False

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        resp = get(self.events_url)
        if not resp or not resp.ok:
            return
        yield from self.custom_parse(resp.text, resp.url)

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script or not script.string:
            return
        try:
            data = json.loads(script.string)
        except Exception:
            return
        exhibitions = (
            data.get("props", {})
                .get("pageProps", {})
                .get("relatedExhibitions", [])
        )
        for exh in exhibitions:
            absolute_url = exh.get("absolute_url", "")
            title = (exh.get("title") or "").strip()
            subtitle = (exh.get("subtitle") or "").strip()
            full_title = f"{title}: {subtitle}" if subtitle else title
            if not full_title:
                continue
            url = f"{BASE}{absolute_url}" if absolute_url else self.events_url

            # Fetch dates from REST API
            start = end = None
            if absolute_url:
                api_url = f"{BASE}/api/gallery{absolute_url}"
                api_resp = get(api_url)
                if api_resp and api_resp.ok:
                    try:
                        api_data = api_resp.json()
                        start_raw = api_data.get("date_start")
                        end_raw = api_data.get("date_end")
                        start = to_la_iso(start_raw) if start_raw else None
                        end = to_la_iso(end_raw) if end_raw else None
                    except Exception:
                        pass

            yield Event(
                id=event_id(self.venue_id, start, full_title + "::exh"),
                venue_id=self.venue_id,
                title=full_title,
                description="",
                event_type="exhibition",
                start=start,
                end=end or start,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
