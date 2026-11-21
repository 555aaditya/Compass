"""Adapters for companies' own public career-site feeds (the JSON their pages load; robots.txt allows them)."""
from datetime import datetime, timezone

import httpx

from app.services.job_discovery.base import RawJob, get_json
from app.services.job_discovery.text import html_to_text


class AmazonAdapter:
    """amazon.jobs search feed, filtered to one country code (board_token, e.g. IND)."""
    name = "amazon"
    PAGE, MAX = 100, 2200

    def fetch(self, company: str, board_token: str, client: httpx.Client) -> list[RawJob]:
        out, offset = [], 0
        while offset < self.MAX:
            data = get_json(client, "https://www.amazon.jobs/en/search.json", params={
                "normalized_country_code[]": board_token or "IND", "result_limit": self.PAGE, "offset": offset, "sort": "recent"})
            jobs = data.get("jobs", [])
            for j in jobs:
                desc = "\n\n".join(html_to_text(j.get(k) or "") for k in ("description", "basic_qualifications", "preferred_qualifications"))
                try:
                    posted = datetime.strptime(j.get("posted_date", ""), "%B %d, %Y").replace(tzinfo=timezone.utc)
                except ValueError:
                    posted = None
                out.append(RawJob(source=self.name, external_id=str(j.get("id_icims") or j.get("id")), title=j.get("title", ""),
                                  company=company, url="https://www.amazon.jobs" + j.get("job_path", ""),
                                  location=j.get("normalized_location") or j.get("location", ""), description_text=desc,
                                  posted_at=posted, country=j.get("country_code", "") or ""))
            offset += self.PAGE
            if len(jobs) < self.PAGE or offset >= data.get("hits", 0):
                break
        return out


class AtlassianAdapter:
    name = "atlassian"

    def fetch(self, company: str, board_token: str, client: httpx.Client) -> list[RawJob]:
        out = []
        for j in get_json(client, "https://www.atlassian.com/endpoint/careers/listings"):
            post = j.get("portalJobPost") or {}
            html = " ".join(j.get(k) or "" for k in ("overview", "responsibilities", "qualifications"))
            try:
                posted = datetime.strptime(post.get("updatedDate", ""), "%Y-%m-%d %I:%M %p").replace(tzinfo=timezone.utc)
            except ValueError:
                posted = None
            locs = j.get("locations") or []
            out.append(RawJob(source=self.name, external_id=str(j.get("id", "")), title=j.get("title", ""), company=company,
                              url=post.get("portalUrl", ""), location="; ".join(l.replace(" - Remote", "") if "India" in l else l for l in locs),
                              description_html=html, description_text=html_to_text(html), posted_at=posted,
                              remote_flag=True if any("Remote" in l for l in locs) else None))
        return out
