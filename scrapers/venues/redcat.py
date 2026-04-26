"""REDCAT — Drupal site with server-rendered Tailwind event cards.

Events are in `a.event-card-stacked` elements. Each card has structured
text in the format: "date | type | type | title | artist?" all separated
by the natural text flow of the card's child elements.
"""
from __future__ import annotations

import re
from typing import Iterable
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil import parser as dparser

from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import now_utc_iso

BASE = "https://www.redcat.org"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year

# Maps REDCAT event type labels → our internal types
_TYPE_MAP = {
    "exhibition": "exhibition",
    "screening": "screening",
    "film": "screening",
    "theater": "performance",
    "theatre": "performance",
    "dance": "performance",
    "music": "performance",
    "talk": "talk",
    "workshop": "workshop",
}


def _parse_range(s: str):
    """Parse 'Apr 4 - Jul 5' or 'Apr 25' (year inferred as current)."""
    s = s.strip().replace("–", "-").replace("—", "-")
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
    venue_id = "redcat"
    events_url = f"{BASE}/events"
    source_label = "redcat.org"

    def custom_parse(self, html: str, base_url: str) -> Iterable[Event]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.find_all("a", class_=re.compile(r"event-card"))
        for card in cards:
            href = card.get("href", "")
            url = href if href.startswith("http") else BASE + href

            # Extract structured text parts from the card
            # Typical format: "Apr 4 - Jul 5 | Exhibition | Exhibition | Title | Artist"
            # We collect text nodes with separators
            parts = [t.strip() for t in card.get_text(separator="|").split("|") if t.strip()]
            if not parts:
                continue

            # First part is usually the date
            date_str = parts[0] if parts else ""
            # Event type is usually the second unique label
            raw_type = parts[1].lower() if len(parts) > 1 else ""
            event_type = _TYPE_MAP.get(raw_type, infer_type(raw_type, ""))

            # Title is the last substantive part (after deduplicated type labels)
            # Skip duplicate type labels
            text_parts = []
            seen = set()
            for p in parts[1:]:
                pl = p.lower()
                if pl not in seen:
                    seen.add(pl)
                    text_parts.append(p)

            # After dedup, remove the type label; remaining parts form artist/title
            if text_parts and text_parts[0].lower() in _TYPE_MAP:
                text_parts = text_parts[1:]
            title = " — ".join(text_parts) if text_parts else ""
            if not title:
                continue

            start, end = _parse_range(date_str) if date_str else (None, None)

            # Image
            img = card.find("img")
            image = None
            if img:
                image = img.get("src") or img.get("data-src")
                if image and image.startswith("/"):
                    image = BASE + image

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=event_type,
                start=start,
                end=end,
                all_day=True,
                url=url,
                image=image,
                artists=[],
                source=self.source_label,
                scraped_at=now_utc_iso(),
            )
