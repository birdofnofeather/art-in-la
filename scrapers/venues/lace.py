"""LACE (Los Angeles Contemporary Exhibitions) — WordPress blog.

Events are published as standard WordPress posts in the "events" category.
The WP REST API returns posts with publication date aligned with event date.
We fetch the 20 most recent posts regardless of date (LACE publishes
infrequently — typically monthly).
"""
from __future__ import annotations

import re
from typing import Iterable
from datetime import datetime, timedelta, timezone

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://welcometolace.org"
_EVENTS_CAT_ID = 8016   # "Events" category


class Scraper(BaseScraper):
    venue_id = "lace"
    events_url = f"{BASE}/events/"
    source_label = "welcometolace.org"

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        # Use WP REST API — ignore the passed-in HTML.
        api_url = (
            f"{BASE}/wp-json/wp/v2/posts"
            f"?categories={_EVENTS_CAT_ID}&per_page=20"
            f"&orderby=date&order=desc"
            f"&_fields=id,title,date,link,excerpt,featured_media"
        )
        resp = get(api_url)
        if not resp or not resp.ok:
            return
        try:
            posts = resp.json()
        except Exception:
            return

        for post in posts:
            raw_title = (post.get("title") or {}).get("rendered", "").strip()
            if not raw_title:
                continue
            raw_title = re.sub(r"<[^>]+>", "", raw_title).strip()

            link = post.get("link", "")
            date_str = post.get("date", "")
            start = (date_str + "-07:00") if date_str and "T" in date_str else None

            excerpt_html = (post.get("excerpt") or {}).get("rendered", "")
            desc = re.sub(r"<[^>]+>", " ", excerpt_html).strip()[:600]

            event_type = infer_type(raw_title, desc)

            image = None
            media_id = post.get("featured_media")
            if media_id:
                media_resp = get(
                    f"{BASE}/wp-json/wp/v2/media/{media_id}?_fields=source_url"
                )
                if media_resp and media_resp.ok:
                    try:
                        image = media_resp.json().get("source_url")
                    except Exception:
                        pass

            yield Event(
                id=event_id(self.venue_id, start, raw_title),
                venue_id=self.venue_id,
                title=raw_title,
                description=desc,
                event_type=event_type,
                start=start,
                end=None,
                all_day=False,
                url=link,
                image=image,
                artists=[],
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
