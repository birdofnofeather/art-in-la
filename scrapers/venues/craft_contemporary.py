"""Craft Contemporary — WordPress custom exhibitions CPT.

The site exposes exhibitions via the WP REST API at /wp-json/wp/v2/exhibition.
Exhibition dates are not in the REST payload; they are scraped from each
individual exhibition page via the `p.craft-exhibition-dates` element.
"""
from __future__ import annotations

import re
from typing import Iterable
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso

BASE = "https://www.craftcontemporary.org"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year


def _parse_range(s: str):
    """Parse 'May 31, 2026 — October 25, 2026' or similar."""
    s = s.strip().replace("–", "-").replace("—", "-").replace("‒", "-")
    parts = re.split(r"\s+-\s+", s, maxsplit=1)
    year_m = _YEAR_RE.search(s)
    year = int(year_m.group(1)) if year_m else _CUR_YEAR
    default = datetime(year, 1, 1)
    try:
        if len(parts) == 1:
            dt = dparser.parse(parts[0], default=default)
            return dt.strftime("%Y-%m-%dT00:00:00-07:00"), None
        start_s, end_s = parts[0].strip(), parts[1].strip()
        if not _YEAR_RE.search(start_s):
            start_s = f"{start_s} {year}"
        start_dt = dparser.parse(start_s, default=default)
        end_dt = dparser.parse(end_s, default=default)
        return (
            start_dt.strftime("%Y-%m-%dT00:00:00-07:00"),
            end_dt.strftime("%Y-%m-%dT00:00:00-07:00"),
        )
    except Exception:
        return None, None


class Scraper(BaseScraper):
    venue_id = "craft_contemporary"
    events_url = f"{BASE}/exhibitions/"
    source_label = "craftcontemporary.org"

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        # Ignore the passed-in HTML; use the WP REST API instead.
        api_url = f"{BASE}/wp-json/wp/v2/exhibition?per_page=20&status=publish&_fields=id,title,link,featured_media"
        resp = get(api_url)
        if not resp or not resp.ok:
            return
        try:
            posts = resp.json()
        except Exception:
            return

        for post in posts:
            link = post.get("link", "")
            raw_title = (post.get("title") or {}).get("rendered", "").strip()
            if not raw_title or not link:
                continue

            # Fetch individual page to extract dates
            page_resp = get(link)
            if not page_resp or not page_resp.ok:
                start, end = None, None
            else:
                page_soup = BeautifulSoup(page_resp.text, "lxml")
                date_el = page_soup.find("p", class_="craft-exhibition-dates")
                date_str = date_el.get_text(strip=True) if date_el else ""
                start, end = _parse_range(date_str) if date_str else (None, None)

                # Skip clearly past exhibitions (end date before now)
                if end:
                    try:
                        end_dt = dparser.parse(end)
                        if end_dt.year < _CUR_YEAR:
                            continue
                    except Exception:
                        pass

            # Featured image
            image = None
            media_id = post.get("featured_media")
            if media_id:
                media_resp = get(f"{BASE}/wp-json/wp/v2/media/{media_id}?_fields=source_url")
                if media_resp and media_resp.ok:
                    try:
                        image = media_resp.json().get("source_url")
                    except Exception:
                        pass

            yield Event(
                id=event_id(self.venue_id, start, raw_title),
                venue_id=self.venue_id,
                title=raw_title,
                description="",
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=link,
                image=image,
                artists=[],
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
