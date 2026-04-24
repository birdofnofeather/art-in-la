"""Polite HTTP client used by all scrapers."""
from __future__ import annotations

import time
from typing import Optional

import requests

USER_AGENT = (
    "ArtInLA-bot/0.1 (+https://github.com/birdofnofeather/art-in-la; "
    "open-source LA art-events aggregator)"
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
