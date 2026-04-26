"""Hauser & Wirth Los Angeles (Downtown).

Parses the Next.js __NEXT_DATA__ blob from the global exhibitions page,
filtered to the Los Angeles location slug.

Note: the site requires a browser User-Agent (Vercel WAF blocks bot UAs),
so _strategy_custom is overridden to use a realistic UA.
"""
from __future__ import annotations

import json
import re
from typing import Iterable

import requests as _requests
from bs4 import BeautifulSoup

from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso

_LA_LOC_RE = re.compile(r"los.angeles", re.I)
_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class Scraper(BaseScraper):
    venue_id = "hauser_wirth"
    events_url = "https://www.hauserwirth.com/hauser-wirth-exhibitions/?location=los-angeles"
    source_label = "hauserwirth.com"

    def _strategy_custom(self):
        """Override to use a browser UA — Vercel WAF blocks the default bot UA."""
        headers = {
            "User-Agent": _BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            resp = _requests.get(self.events_url, headers=headers, timeout=25)
        except Exception as e:
            print(f"  [{self.venue_id}] custom fetch error: {e}")
            return
        if not resp or resp.status_code != 200:
            print(f"  [{self.venue_id}] custom fetch status: {resp.status_code if resp else 'None'}")
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

        items = (
            data.get("props", {})
                .get("pageProps", {})
                .get("initialExhibitionsData", {})
                .get("galleryExhibitionCollection", {})
                .get("items", [])
        )

        for it in items:
            locs = it.get("relatedLocationsCollection", {}).get("items", [])
            loc_slugs = [loc.get("slug", "") for loc in locs if isinstance(loc, dict)]
            # If location list is non-empty, filter to LA only
            if locs and not any(_LA_LOC_RE.search(s) for s in loc_slugs):
                continue

            title = (it.get("title") or "").strip()
            if not title:
                continue

            slug = it.get("slug", "")
            start = to_la_iso(it.get("startDate"))
            end = to_la_iso(it.get("endDate"))
            url = (
                f"https://www.hauserwirth.com/hauser-wirth-exhibitions/{slug}/"
                if slug else None
            )

            images = it.get("listingPageImage") or []
            image = images[0].get("src") if images and isinstance(images[0], dict) else None

            artists = []
            for a in it.get("relatedArtistsCollection", {}).get("items", []):
                if not isinstance(a, dict):
                    continue
                first = (a.get("firstName") or "").strip()
                last = (a.get("lastName") or "").strip()
                name = f"{first} {last}".strip()
                if name:
                    artists.append(name)

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=image,
                artists=artists,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )

            opening = it.get("openingReception")
            if opening:
                open_start = to_la_iso(opening)
                open_text = (it.get("openingReceptionText") or "").strip()
                yield Event(
                    id=event_id(self.venue_id, open_start, title + "::opening"),
                    venue_id=self.venue_id,
                    title=f"{title} — Opening Reception",
                    description=open_text,
                    event_type="opening",
                    start=open_start,
                    end=None,
                    all_day=False,
                    url=url,
                    image=image,
               