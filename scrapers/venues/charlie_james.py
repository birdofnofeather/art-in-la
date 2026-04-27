"""charlie_james — Squarespace/HTML, article containers with inline date."""
from __future__ import annotations
import re
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso
BASE = "https://www.cjamesgallery.com"
_DATE_RE = re.compile(
    r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+\d{1,2}(?:st|nd|rd|th)?\s*[-–—]\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?"
    r"|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?"
    r"|Nov(?:ember)?|Dec(?:ember)?)\.?\s+)?\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{2,4})",re.IGNORECASE)
_SKIP=re.compile(r"^(exhibitions|current exhibitions|current|upcoming|past|news)$",re.IGNORECASE)
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
    venue_id = "charlie_james"
    events_url = f"{BASE}/exhibitions"
    source_label = "cjamesgallery.com"
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
        containers=soup.find_all("article") or soup.find_all("section")
        for c in containers:
            text=c.get_text(" ",strip=True)
            if not text or len(text)<10: continue
            m=_DATE_RE.search(text)
            if not m: continue
            tel=c.find(["h1","h2","h3","h4"])
            if not tel: continue
            title=tel.get_text(strip=True)
            if not title or _SKIP.match(title) or title in seen or len(title)<3: continue
            seen.add(title)
            start,end=_pr(m.group(0))
            a=c.find("a",href=True); href=a["href"] if a else ""
            url=href if href.startswith("http") else (f"{BASE}{href}" if href else self.events_url)
            img=c.find("img"); image=img.get("src") if img else None
            yield Event(id=event_id(self.venue_id,start,title),venue_id=self.venue_id,
                title=title,description="",event_type=infer_type(title,text[:200]),
                start=start,end=end,all_day=True,url=url,image=image,
                source=self.source_label,scraped_at=now_utc_iso())
