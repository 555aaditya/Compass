from datetime import datetime

import httpx

from app.services.job_discovery.base import RawJob, SourceError, get_json
from app.services.job_discovery.greenhouse import parse_dt
from app.services.job_discovery.text import html_to_text
from app.services.job_matching import eligibility
from app.services.job_matching.preferences import Preferences

API = "https://api.smartrecruiters.com/v1/companies"


class SmartRecruitersAdapter:
    """Public SmartRecruiters posting API. Descriptions need one request per posting, so we only
    fetch them for postings that survive a title/location pre-filter."""
    name = "smartrecruiters"
    MAX_POSTINGS = 600

    def fetch(self, company: str, board_token: str, client: httpx.Client) -> list[RawJob]:
        prefs, items, offset = Preferences(), [], 0
        while offset < self.MAX_POSTINGS:
            page = get_json(client, f"{API}/{board_token}/postings", params={"limit": 100, "offset": offset})
            content = page.get("content", [])
            items += content
            offset += 100
            if len(content) < 100 or offset >= page.get("totalFound", 0):
                break
        out = []
        for it in items:
            loc = it.get("location") or {}
            location = ", ".join(x for x in (loc.get("city"), loc.get("region"), (loc.get("country") or "").upper()) if x)
            if loc.get("remote"):
                location = (location + " (Remote)").strip()
            posted = parse_dt(it.get("releasedDate"))
            e = eligibility.evaluate(it.get("name", ""), location, "", posted, prefs, loc.get("remote"), loc.get("country", ""))
            if e.status == "rejected":
                continue
            desc = ""
            try:
                d = get_json(client, f"{API}/{board_token}/postings/{it['id']}", attempts=2)
                secs = (d.get("jobAd") or {}).get("sections") or {}
                desc = "\n\n".join(html_to_text(s.get("text", "")) for s in secs.values() if isinstance(s, dict))
                url = d.get("postingUrl") or d.get("applyUrl") or ""
            except SourceError:
                url = ""
            out.append(RawJob(source=self.name, external_id=it.get("id", ""), title=it.get("name", ""), company=company,
                              url=url or f"https://jobs.smartrecruiters.com/{board_token}/{it.get('id', '')}",
                              location=location, description_text=desc, posted_at=posted,
                              remote_flag=True if loc.get("remote") else None, country=loc.get("country", "") or ""))
        return out
