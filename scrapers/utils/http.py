"""Polite HTTP client used by all scrapers."""
from __future__ import annotations

import time
from typing import Optional

import requests

# Several venue sites (Norton Simon, Armory, etc.) return 403/429 to non-browser
# User-Agents, so we present a current desktop-Chrome UA. We stay polite: low
# request volume, retries with backoff, and a single daily run.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

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
            return resp  # non-200 but not retryable; caller can inspect
        except (requests.RequestException, OSError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff ** attempt)
                continue
    if last_err:
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
