"""luis_de_jesus — Artlogic CMS div.entry h1/h2/h3."""
from __future__ import annotations
import re
from typing import Iterable
from datetime import datetime
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from ..base import BaseScraper, Event
from ..utils.event_id import event_id
from ..utils.dateparse import now_utc_iso
BASE = "https://www.luisdejesus.com"
_YEAR_RE = re.compile(r"\b(20\d\d)\b")
_CUR_YEAR = datetime.now().year
def _pr(s):
    s = s.strip().replace("–","-").replace("—","-")
    parts = re.split(r"\s+-\s+", s, maxsplit=1)
    ym = _YEAR_RE.search(s); yr = int(ym.group(1)) if ym else _CUR_YEAR
    d = datetime(yr,1,1)
    try:
        if len(parts)==1: dt=dparser.parse(parts[0],default=d); return dt.strftime("%Y-%m-%dT00:00:00-07:00"),None
        s0,s1=parts[0].strip(),parts[1].strip()
        if not _YEAR_RE.search(s0): s0=f"{s0} {yr}"
        return dparser.parse(s0,default=d).strftime("%Y-%m-%dT00:00:00-07:00"),dparser.parse(s1,default=d).strftime("%Y-%m-%dT00:00:00-07:00")
    except: return None,None
class Scraper(BaseScraper):
    venue_id = "luis_de_jesus"
    events_url = f"{BASE}/exhibitions"
    source_label = "luisdejesus.com"
    def custom_parse(self, html, base_url):
        soup = BeautifulSoup(html,"lxml")
        sec = soup.find("section",{"id":"exhibitions-container-main"}) or soup
        for e in sec.find_all("div",class_="entry"):
            a=e.find("a",href=True)
            if not a: continue
            href=a["href"]; url=href if href.startswith("http") else BASE+href
            h1=e.find("h1"); h2=e.find("h2"); h3=e.find("h3")
            artist=h1.get_text(strip=True) if h1 else ""
            show=h2.get_text(strip=True) if h2 else ""
            date=h3.get_text(strip=True) if h3 else ""
            title=f"{artist}: {show}" if show else artist
            if not title: continue
            start,end=_pr(date) if date else (None,None)
            img=e.find("img"); image=(img.get("src") or img.get("data-src")) if img else None
            yield Event(id=event_id(self.venue_id,start,title),venue_id=self.venue_id,
                title=title,description="",event_type="exhibition",start=start,end=end,
                all_day=True,url=url,image=image,artists=[artist] if artist else [],
                source=self.source_label,scraped_at=now_utc_iso())
