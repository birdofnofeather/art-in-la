"""USC Fisher Museum of Art — WordPress with custom 'exhibitions' post type + ACF."""
from __future__ import annotations

import re
from typing import Iterable

from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso

BASE = "https://fisher.usc.edu"
LA_OFFSET = "-07:00"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")


def _parse_range(s: str):
    """Parse 'April 17 – May 3,  2026' -> (start_iso, end_iso)."""
    if not s:
        return None, None
    s = s.strip().replace("–", "-").replace("—", "-").replace("‒", "-")
    parts = re.split(r"\s+-\s+", s, maxsplit=1)
    year_m = _YEAR_RE.search(s)
    from datetime import datetime
    year = int(year_m.group(1)) if year_m else datetime.now().year
    default = datetime(year, 1, 1)
    try:
        if len(parts) == 1:
            dt = dparser.parse(parts[0], default=default, fuzzy=True)
            return dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"), None
        start_s, end_s = parts[0].strip(), parts[1].strip()
        if not _YEAR_RE.search(start_s):
            start_s = f"{start_s} {year}"
        start_dt = dparser.parse(start_s, default=default, fuzzy=True)
        end_dt = dparser.parse(end_s, default=default, fuzzy=True)
        return (
            start_dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"),
            end_dt.strftime(f"%Y-%m-%dT00:00:00{LA_OFFSET}"),
        )
    except Exception:
        return None, None


class Scraper(BaseScraper):
    venue_id = "usc_fisher"
    events_url = f"{BASE}/exhibitions"
    source_label = "fisher.usc.edu"
    drop_exhibitions = False

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        # WP REST API for custom post type 'exhibitions' with ACF date field
        url = f"{BASE}/wp-json/wp/v2/exhibitions?per_page=20&_fields=id,title,link,acf,excerpt"
        resp = get(url)
        if not resp or not resp.ok:
            return

        try:
            items = resp.json()
        except Exception:
            return

        seen: set[str] = set()
        for item in items:
            title = (item.get("title") or {}).get("rendered", "").strip()
            if not title or title in seen:
                continue
            seen.add(title)

            url_link = item.get("link", self.events_url)

            # ACF date field: "April 17 – May 3,  2026"
            acf = item.get("acf") or {}
            date_val = ""
            if isinstance(acf, dict):
                date_field = acf.get("date") or {}
                if isinstance(date_field, dict):
                    date_val = date_field.get("value", "") or date_field.get("simple_value_formatted", "")
                elif isinstance(date_field, str):
                    date_val = date_field

            start, end = _parse_range(date_val)

            desc = (item.get("excerpt") or {}).get("rendered", "")
            desc = re.sub(r"<[^>]+>", " ", desc).strip()

            yield Event(
                id=event_id(self.venue_id, start, title + "::exh"),
                venue_id=self.venue_id,
                title=title,
                description=desc[:800],
                event_type="exhibition",
                start=start,
                end=end,
                all_day=True,
                url=url_link,
                image=None,
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
