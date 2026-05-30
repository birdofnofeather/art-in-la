"""Gallery Luisotti — h2 blocks on exhibitions-current page."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.dateparse import to_la_iso, now_utc_iso
BASE = "https://galleryluisotti.com"
_DATE_RE = re.compile(
    r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+\d{1,2}(?:st|nd|rd|th)?\s*[-–—]\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?"
    r"|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?"
    r"|Nov(?:ember)?|Dec(?:ember)?)\.?\s+)?\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})",re.IGNORECASE)
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
    venue_id = "gallery_luisotti"
    events_url = f"{BASE}/exhibitions-current/"
    source_label = "galleryluisotti.com"
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
        for h2 in soup.find_all("h2"):
            parent=h2.find_parent(["div","section","article"])
            text=parent.get_text(" ",strip=True) if parent else h2.get_text(" ",strip=True)
            m=_DATE_RE.search(text)
            if not m: continue
            title=_DATE_RE.sub("",h2.get_text(" ",strip=True)).strip()
            if not title or title in seen or len(title)<3: continue
            seen.add(title)
            start,end=_pr(m.group(0))
            a=(parent or h2).find("a",href=True); href=a["href"] if a else ""
            url=href if href.startswith("http") else (f"{BASE}{href}" if href else self.events_url)
            yield Event(id=event_id(self.venue_id,start,title),venue_id=self.venue_id,
                title=title,description="",event_type="exhibition",start=start,end=end,
                all_day=True,url=url,image=None,source=self.source_label,scraped_at=now_utc_iso())
