"""Matthew Marks Gallery – Los Angeles exhibitions."""
from __future__ import annotations
import re
from typing import Iterable
from bs4 import BeautifulSoup
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso

BASE = "https://matthewmarks.com"
MON = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RE = re.compile(
    r"through\s+(" + MON + r"\s+\d{1,2},?\s*\d{4})"
    r"|(" + MON + r"\s+\d{1,2}\s*[-–]\s*" + MON + r"\s+\d{1,2},?\s*\d{4})",
    re.I,
)


class Scraper(BaseScraper):
    venue_id = "matthew_marks"
    events_url = f"{BASE}/exhibitions/current"
    source_label = "matthewmarks.com"

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
        now = now_utc_iso()
        seen: set[str] = set()
        for fig in soup.find_all("figure", class_="los-angeles"):
            a = fig.find("a", href=True)
            if not a:
                continue
            href = a["href"]
            url = href if href.startswith("http") else BASE + href
            if url in seen:
                continue
            seen.add(url)

            # Title is in a <p> tag (h1 is present but empty)
            title = ""
            cap = fig.find(class_=re.compile(r"caption|title", re.I)) or fig
            for el in cap.find_all(["h1","h2","h3","h4","p","strong"]):
                t = el.get_text(strip=True)
                if t and not re.search(r"through|until|address|location", t, re.I):
                    title = t
                    break
            if not title:
                title = fig.get_text(strip=True)[:80]
            title = title.strip()
            if not title:
                continue

            txt = fig.get_text(separator=" ", strip=True)
            m = _DATE_RE.search(txt)
            date_str = (m.group(1) or m.group(2)) if m else ""
            start = to_la_iso(date_str) if date_str else None

            yield Event(
                id=event_id(self.venue_id, start, title),
                venue_id=self.venue_id,
                title=title,
                description="",
                event_type=("opening" if re.search(r"(opening|reception|vernissage|preview)", title, re.I) else "exhibition"),
                start=start,
                end=start,
                all_day=True,
                url=url,
                image=None,
                source=self.source_label,
                scraped_at=now,
            )
