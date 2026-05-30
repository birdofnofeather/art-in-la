"""Honor Fraser Gallery — WordPress with Alpine.js / AJAX backend.

The /programming page fetches cpt_programs records via WP admin-ajax.php.
We:
  1. GET /programming to extract ajax_nonce + ajaxurl
  2. POST to ajaxurl with action=get_records, post_type=cpt_programs
  3. Parse recordsCurrent + recordsUpcoming from the JSON response

Each record contains:
  - title, url, imageUrl, category_slug, date (HTML with itemprop startDate/endDate)
  - category_slug: solo-exhibition, group-exhibition, event, other, etc.
"""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso
from ..utils.http import get, post_form

BASE = "https://honorfraser.com"
_PROG_URL = f"{BASE}/programming/"
_DATE_CONTENT_RE = re.compile(r'content="(\d{4}-\d{2}-\d{2})"')


def _slug_to_event_type(slug: str) -> str:
    slug = (slug or "").lower()
    if "exhibition" in slug:
        return "exhibition"
    if "opening" in slug or "reception" in slug or "vernissage" in slug:
        return "opening"
    return "event"


def _parse_dates(date_html: str):
    """Extract start/end ISO dates from the <nobr itemprop> HTML snippet."""
    dates = _DATE_CONTENT_RE.findall(date_html or "")
    if not dates:
        return None, None
    start = dates[0] + "T00:00:00-07:00"
    end = dates[1] + "T00:00:00-07:00" if len(dates) > 1 and dates[1] else None
    return start, end


class Scraper(BaseScraper):
    venue_id = "honor_fraser"
    events_url = _PROG_URL
    source_label = "honorfraser.com"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        # Step 1: fetch programming page for nonce
        resp = get(_PROG_URL)
        if not resp or not resp.ok:
            return
        html = resp.text
        nonce_m = re.search(r'"ajax_nonce"\s*:\s*"([a-f0-9]+)"', html)
        ajax_m = re.search(r'"ajaxurl"\s*:\s*"(https?://[^"]+/admin-ajax\.php)"', html)
        if not nonce_m or not ajax_m:
            return
        nonce = nonce_m.group(1)
        ajax_url = ajax_m.group(1)

        # Step 2: fetch all records (page=0 returns current+upcoming+past)
        data = {
            "action": "get_records",
            "post_type": "cpt_programs",
            "filterCategory": "",
            "search": "",
            "page": "0",
            "security": nonce,
        }
        api_resp = post_form(ajax_url, data)
        if not api_resp or not api_resp.ok:
            return
        try:
            payload = api_resp.json()
        except Exception:
            return
        if not payload.get("success"):
            return

        now = now_utc_iso()
        seen: set[str] = set()
        d = payload["data"]
        records = list(d.get("recordsCurrent", [])) + list(d.get("recordsUpcoming", []))

        for rec in records:
            url = rec.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)

            title = (rec.get("title") or "").strip()
            if not title:
                continue

            slug = rec.get("category_slug", "")
            event_type = _slug_to_event_type(slug)

            date_html = rec.get("date", "")
            start, end = _parse_dates(date_html)

            # For openings: check if title has explicit opening keyword
            if event_type == "exhibition":
                import re as _re
                if _re.search(r"\b(opening|reception|vernissage|preview)\b", title, _re.I):
                    event_type = "opening"

            image = rec.get("imageUrl") or None
            location = (rec.get("location") or "").strip()
            desc = location

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description=desc,
                event_type=event_type,
                start=start,
                end=end,
                all_day=(event_type == "exhibition"),
                url=url,
                image=image,
                source=self.source_label,
                scraped_at=now,
            )
