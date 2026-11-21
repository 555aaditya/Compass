"""Common job-source adapter interface plus a retrying HTTP helper."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import httpx

log = logging.getLogger(__name__)
USER_AGENT = "compass-job-finder/1.0 (personal use; public job board APIs)"


@dataclass
class RawJob:
    """A posting exactly as a source reports it, before normalisation."""
    source: str
    external_id: str
    title: str
    company: str
    url: str
    location: str = ""
    description_html: str = ""
    description_text: str = ""
    posted_at: datetime | None = None
    remote_flag: bool | None = None
    country: str = ""


class SourceError(Exception):
    pass


class JobSourceAdapter(Protocol):
    name: str

    def fetch(self, company: str, board_token: str, client: httpx.Client) -> list[RawJob]: ...


def make_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                        timeout=httpx.Timeout(20.0), follow_redirects=True)


def get_json(client: httpx.Client, url: str, *, attempts: int = 3, backoff: float = 1.0, **kw):
    """GET JSON with exponential backoff on network errors, 429 and 5xx. 404 raises immediately."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            r = client.get(url, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                retry_after = r.headers.get("retry-after", "")
                delay = float(retry_after) if retry_after.isdigit() else backoff * 2 ** i
                last = SourceError(f"HTTP {r.status_code} from {url}")
                if i < attempts - 1:
                    time.sleep(min(delay, 30))
                continue
            if r.status_code >= 400:
                raise SourceError(f"HTTP {r.status_code} from {url}")
            return r.json()
        except (httpx.TransportError, ValueError) as exc:
            last = SourceError(f"{type(exc).__name__}: {exc}")
            if i < attempts - 1:
                time.sleep(backoff * 2 ** i)
    raise last or SourceError("request failed")
