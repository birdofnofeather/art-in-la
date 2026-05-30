"""Karma Gallery LA — filter exhibition links to Los Angeles."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso
BASE = "https://karmakarma.org"
_DATE_RE = re.compile(
    r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+\d{1,2}(?:st|nd|rd|th)?\s*[-–—]\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?"
    r"|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?"
    r"|Nov(?:ember)?|Dec(?:ember)?)\.?\s+)?\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})",re.IGNORECASE)
_LA = re.compile(r"santa monica|los angeles|silver lake|highland park|7351",re.IGNORECASE)
def _pr(raw):
    raw=re.sub(r"[–—]"," - ",raw); parts=[p.strip() for p in re.split(r"\s+-\s+",raw,maxsplit=1)]
    s=e=None
    try: s=to_la_iso(du_parser.parse(parts[0],fuzzy=True))
    except: pass
    if len(parts)>1:
        try: e=to_la_iso(du_parser.parse(parts[1],fuzzy=True))
        except: e=s
    return s,e or s
class Scraper(BaseScraper):
    venue_id = "karma_la"
    events_url = f"{BASE}/exhibitions/"
    source_label = "karmakarma.org"
    def _strategy_wp_tribe(self): return iter([])
    def _strategy_ical(self): return iter([])
    def _strategy_jsonld(self): return iter([])
    def _strategy_feed(self): return iter([])
    def _strategy_custom(self):
        resp=get(self.events_url)
        if not resp or not resp.ok: return
        yield from self.custom_parse(resp.text,resp.url)
    def custom_parse(self,html,base_url):
        soup=BeautifulSoup(html,"lxml"); seen=set()
        for a in soup.find_all("a",href=True):
            href=a.get("href","")
            if "/exhibitions/" not in href or len(href.split("/"))<4: continue
            parent=a.find_parent(["div","li","article"])
            if not parent: continue
            text=parent.get_text(" ",strip=True)
            if not _LA.search(text) and "-la-" not in href: continue
            m=_DATE_RE.search(text)
            if not m: continue
            title=text[:m.start()].strip().rstrip(":")
            title=re.sub(r"^current\s*","",title,flags=re.IGNORECASE).strip()
            if not title or title in seen or len(title)<3: continue
            seen.add(title)
            start,end=_pr(m.group(0))
            url=href if href.startswith("http") else f"{BASE}{href}"
            yield Event(id=event_id(self.venue_id,start,title),venue_id=self.venue_id,
                title=title,description="",event_type="exhibition",start=start,end=end,
                all_day=True,url=url,image=None,source=self.source_label,scraped_at=now_utc_iso())
