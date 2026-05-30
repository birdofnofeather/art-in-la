"""Steve Turner Gallery — custom WordPress theme.

/time/current  – current exhibitions (often JS-rendered / empty at scrape time)
/time/past     – past exhibitions (server-rendered)

Each entry: div.colt-col-4 with exh-title, exh-sub, excerpt > p (dates), img.
Only includes shows with explicit 4-digit year in the date string.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Iterable
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso
from ..utils.http import get

BASE = "http://steveturner.la"
_PAGES = [f"{BASE}/time/current", f"{BASE}/time/past"]
_YEAR_RE = re.compile(r"\b(20\d\d)\b")


def _parse_range(text: str):
    """Parse 'Month D – Month D, YYYY'. Returns (start_iso, end_iso) or (None, None)."""
    text = text.strip()
    if not _YEAR_RE.search(text):
        return None, None
    year = int(_YEAR_RE.search(text).group(1))
    default = datetime(year, 1, 1)
    parts = re.split(r"\s*[\u2013\u2014-]\s*", text, maxsplit=1)
    try:
        s = parts[0].strip()
        if not _YEAR_RE.search(s):
            s = f"{s} {year}"
        start_dt = dparser.parse(s, default=default, fuzzy=True)
        s_iso = start_dt.strftime("%Y-%m-%dT00:00:00-07:00")
        if len(parts) == 2:
            e = parts[1].strip()
            if not _YEAR_RE.search(e):
                e = f"{e} {year}"
            end_dt = dparser.parse(e, default=start_dt, fuzzy=True)
            e_iso = end_dt.strftime("%Y-%m-%dT00:00:00-07:00")
        else:
            e_iso = None
        return s_iso, e_iso
    except Exception:
        return None, None


class Scraper(BaseScraper):
    venue_id = "steve_turner"
    events_url = f"{BASE}/time/current"
    source_label = "steveturner.la"

    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])

    def _strategy_custom(self) -> Iterable[Event]:
        seen: set[str] = set()
        now_str = now_utc_iso()
        for page_url in _PAGES:
            resp = get(page_url)
            if not resp or not resp.ok:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for col in soup.find_all("div", class_="colt-col-4"):
                a_tag = col.find("a", href=True)
                if not a_tag:
                    continue
                href = a_tag["href"]
                url = href if href.startswith("http") else BASE + href
                if url in seen:
                    continue
                seen.add(url)

                show_title = ""
                artist = ""
                t_el = col.find("div", class_="exh-title")
                s_el = col.find("div", class_="exh-sub")
                if t_el:
                    show_title = t_el.get_text(strip=True)
                if s_el:
                    artist = s_el.get_text(strip=True)

                title = show_title if show_title else artist
                if not title:
                    continue

                date_text = ""
                excerpt = col.find("div", class_="excerpt")
                if excerpt:
                    for p in excerpt.find_all("p"):
                        txt = p.get_text(strip=True)
                        if txt and "Read more" not in txt:
                            date_text = txt
                            break

                start, end = _parse_range(date_text) if date_text else (None, None)

                # If no year found in date text, skip — can't verify freshness
                if date_text and not _YEAR_RE.search(date_text):
                    continue

                # Skip shows that ended more than 12 months ago
                if end:
                    try:
                        end_dt = dparser.parse(end)
                        now_dt = datetime.now(tz=timezone.utc)
                        cutoff = now_dt.replace(year=now_dt.year - 1)
                        if end_dt.replace(tzinfo=timezone.utc) < cutoff:
                            continue
                    except Exception:
                        pass

                img_tag = col.find("img")
                image = img_tag.get("src") or img_tag.get("data-src") if img_tag else None
                full_title = f"{artist}: {show_title}" if artist and show_title else title

                yield Event(
                    id=event_id(self.venue_id, start, full_title),
                    venue_id=self.venue_id,
                    title=full_title,
                    description="",
                    event_type="exhibition",
                    start=start,
                    end=end,
                    all_day=True,
                    url=url,
                    image=image,
                    artists=[artist] if artist else [],
                    source=self.source_label,
                    scraped_at=now_str,
                )
