"""Las Fotos Project — Squarespace article cards.

The listing cards carry both the date and a clock time (often a range like
"6:00 PM – 8:00 PM"), using narrow no-break spaces. We attach the time to
single-date events; multi-date programs keep an all-day date range, since a
single session time can't represent the whole run.
"""
from __future__ import annotations
import re
from datetime import datetime
from bs4 import BeautifulSoup
from dateutil import parser as du_parser
from ..base import BaseScraper, Event
from ..utils.http import get
from ..utils.event_id import event_id
from ..utils.event_type import infer as infer_type
from ..utils.dateparse import to_la_iso, now_utc_iso
BASE = "https://www.lasfotosproject.org"
_CUR_YEAR = datetime.now().year
_MONTH = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
          r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")
_DATE_RE = re.compile(
    _MONTH + r"\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?"
    r"(?:\s*[-–—]\s*(?:" + _MONTH + r"\.?\s+)?\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})?",
    re.IGNORECASE)
# Is the matched date actually a range ("July 8 – August 12")?
_RANGE_RE = re.compile(r"\d\s*[-–—]\s*(?:" + _MONTH + r"|\d)", re.IGNORECASE)

_AMPM = r"[ap]\.?m\.?"
_TIME_RANGE_RE = re.compile(
    r"(\d{1,2})(?::(\d{2}))?\s*(?:(" + _AMPM + r")\s*)?[–—-]\s*"
    r"(\d{1,2})(?::(\d{2}))?\s*(" + _AMPM + r")", re.IGNORECASE)
_SINGLE_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(" + _AMPM + r")", re.IGNORECASE)


def _to24(h: int, m: int, ap: str) -> tuple[int, int]:
    ap = ap.lower().replace(".", "")
    if ap.startswith("p") and h != 12:
        h += 12
    elif ap.startswith("a") and h == 12:
        h = 0
    return h, m


class Scraper(BaseScraper):
    venue_id = "las_fotos_project"
    events_url = f"{BASE}/events"
    source_label = "lasfotosproject.org"
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
        for art in soup.find_all("article"):
            tel=art.find(["h1","h2","h3","h4"])
            if not tel: continue
            title=tel.get_text(strip=True)
            if not title or title in seen or len(title)<3: continue
            seen.add(title)
            # Normalize narrow/no-break spaces so the time regexes match.
            text=art.get_text(" ",strip=True).replace(" "," ").replace("\xa0"," ")
            m=_DATE_RE.search(text)
            start=None; end=None; all_day=True
            if m:
                date_text=m.group(0)
                is_range=bool(_RANGE_RE.search(date_text))
                try:
                    d0=du_parser.parse(date_text,fuzzy=True,default=datetime(_CUR_YEAR,1,1))
                except Exception:
                    d0=None
                if d0 and not is_range:
                    start,end,all_day=self._timed(d0,text)
                elif d0:
                    start=to_la_iso(d0.date().isoformat(),all_day=True)
            a=art.find("a",href=True); href=a["href"] if a else ""
            url=href if href.startswith("http") else (f"{BASE}{href}" if href else self.events_url)
            img=art.find("img"); image=img.get("src") if img else None
            yield Event(id=event_id(self.venue_id,start,title),venue_id=self.venue_id,
                title=title,description="",event_type=infer_type(title,text[:200]),
                start=start,end=end,all_day=all_day,url=url,image=image,
                source=self.source_label,scraped_at=now_utc_iso())

    def _timed(self, d0, text):
        """Return (start_iso, end_iso, all_day) for a single-date card."""
        tr=_TIME_RANGE_RE.search(text)
        if tr:
            end_ap=tr.group(6); start_ap=tr.group(3) or end_ap
            sh,sm=_to24(int(tr.group(1)),int(tr.group(2) or 0),start_ap)
            eh,em=_to24(int(tr.group(4)),int(tr.group(5) or 0),end_ap)
            start=to_la_iso(datetime(d0.year,d0.month,d0.day,sh,sm))
            end=to_la_iso(datetime(d0.year,d0.month,d0.day,eh,em))
            return start,end,False
        st=_SINGLE_TIME_RE.search(text)
        if st:
            sh,sm=_to24(int(st.group(1)),int(st.group(2) or 0),st.group(3))
            return to_la_iso(datetime(d0.year,d0.month,d0.day,sh,sm)),None,False
        return to_la_iso(d0.date().isoformat(),all_day=True),None,True
