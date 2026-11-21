from datetime import datetime

import httpx

from app.services.job_discovery.base import RawJob, get_json
from app.services.job_discovery.text import html_to_text


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


class GreenhouseAdapter:
    name = "greenhouse"

    def fetch(self, company: str, board_token: str, client: httpx.Client) -> list[RawJob]:
        data = get_json(client, f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs",
                        params={"content": "true"})
        out = []
        for j in data.get("jobs", []):
            content = j.get("content", "")
            out.append(RawJob(
                source=self.name, external_id=str(j.get("id", "")), title=j.get("title", ""),
                company=company, url=j.get("absolute_url", ""),
                location=(j.get("location") or {}).get("name", ""),
                description_html=content, description_text=html_to_text(content),
                posted_at=parse_dt(j.get("first_published") or j.get("updated_at")),
            ))
        return out
