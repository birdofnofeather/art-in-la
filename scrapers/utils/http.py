"""Polite HTTP client used by all scrapers."""
from __future__ import annotations

import time
from typing import Optional

import requests

# Several venue sites (Norton Simon, Armory, etc.) return 403/429 to non-browser
# User-Agents, so we present a current desktop-Chrome UA. We stay polite: low
# request volume, retries with backoff, and a single daily run.
def _chrome_major(today=None) -> int:
    """A current Chrome major version, derived from the date.

    The UA used to be hard-coded "Chrome/124". By late 2026 that was ~30
    months stale, and university WAFs (USC Fisher, USC Pacific Asia Museum,
    UCLA Fowler) began resetting connections that claimed it — four museums
    silently produced nothing from Sept 1. Chrome ships a major version every
    4 weeks (124 on 2024-04-16), so derive it; stay 2 versions behind the
    newest, which is what most real browsers report.
    """
    import datetime as _dt
    today = today or _dt.date.today()
    return 124 + max(0, (today - _dt.date(2024, 4, 16)).days // 28) - 2


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    f"(KHTML, like Gecko) Chrome/{_chrome_major()}.0.0.0 Safari/537.36"
)
# Tried once if a site resets the connection on the browser UA.
FALLBACK_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"

DEFAULT_TIMEOUT = 20

_session: Optional[requests.Session] = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,"
                     "application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        })
        _session = s
    return _session


def get(url: str, *, timeout: int = DEFAULT_TIMEOUT, retries: int = 2,
        backoff: float = 1.5, headers: Optional[dict] = None) -> Optional[requests.Response]:
    """GET with retries and exponential backoff. Returns None on final failure."""
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = session().get(url, timeout=timeout, headers=headers, allow_redirects=True)
            if resp.status_code == 200:
                return resp
            if 500 <= resp.status_code < 600 and attempt < retries:
                time.sleep(backoff ** attempt)
                continue
            if resp.status_code == 429 and attempt < retries:
                # Rate-limited: honor Retry-After when it's a sane number of
                # seconds, otherwise fall back to exponential backoff.
                wait = backoff ** attempt
                try:
                    wait = min(float(resp.headers.get("Retry-After", wait)), 30.0)
                except (TypeError, ValueError):
                    pass
                time.sleep(wait)
                continue
            return resp  # non-200 but not retryable; caller can inspect
        except Exception as e:  # noqa: BLE001 — a malformed body (bad gzip,
            # zlib.error) must fail this one fetch, never crash the venue.
            last_err = e
            if attempt < retries:
                time.sleep(backoff ** attempt)
                continue
    if last_err is not None:
        # Connection reset on our browser identity: try once as Safari before
        # giving up (some WAFs fingerprint one UA family, not the other).
        try:
            h = dict(headers or {}); h["User-Agent"] = FALLBACK_UA
            resp = session().get(url, timeout=timeout, headers=h, allow_redirects=True)
            print(f"  [http] {url}: recovered with fallback UA ({resp.status_code})")
            return resp
        except Exception:  # noqa: BLE001
            pass
        print(f"  [http] giving up on {url}: {last_err}")
    return None


def post_form(url: str, data: dict, *, timeout: int = DEFAULT_TIMEOUT) -> Optional[requests.Response]:
    """POST form-encoded data. Returns None on failure."""
    try:
        resp = session().post(url, data=data, timeout=timeout)
        return resp
    except (requests.RequestException, OSError) as e:
        print(f"  [http] POST failed on {url}: {e}")
        return None
