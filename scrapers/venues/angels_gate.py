"""Angels Gate Cultural Center — WordPress article cards, skip PAST/CANCELED."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso
BASE = "https://angelsgateart.org"
_DATE_RE = re.compile(
    r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?)",re.IGNORECASE)
_SKIP = re.compile(r"^\s*(PAST|CANCELED|CANCELLED|POSTPONED)[:\s]",re.IGNORECASE)
class Scraper(BaseScraper):
    venue_id = "angels_gate"
    events_url = f"{BASE}/events"
    source_label = "angelsgateart.org"
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_custom(self):
        resp=get(self.events_url)
        if not resp or not resp.ok: return
        yield from self.custom_parse(resp.text,resp.url)
    def custom_parse(self,html,base_url):
        soup=BeautifulSoup(html,"lxml"); seen=set()
        for art in soup.find_all("article"):
            tel=art.find(["h1","h2","h3","h4"])
            if not tel: continue
            title=tel.get_text(strip=True)
            if _SKIP.match(title) or title in seen or len(title)<3: continue
            seen.add(title)
            a=art.find("a",href=True); href=a["href"] if a else ""
            url=href if href.startswith("http") else f"{BASE}{href}"
            text=art.get_text(" ",strip=True)
            m=_DATE_RE.search(text)
            start=None
            if m:
                try: start=to_la_iso(du_parser.parse(m.group(0),fuzzy=True))
                except: pass
            img=art.find("img"); image=img.get("src") if img else None
            yield Event(id=event_id(self.venue_id,start,title),venue_id=self.venue_id,
                title=title,description="",event_type=infer_type(title,""),start=start,
                end=None,all_day=False,url=url,image=image,source=self.source_label,scraped_at=now_utc_iso())
