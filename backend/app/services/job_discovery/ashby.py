import httpx

from app.services.job_discovery.base import RawJob, get_json
from app.services.job_discovery.greenhouse import parse_dt


class AshbyAdapter:
    """Uses Ashby's official public posting API (not the internal GraphQL endpoint)."""
    name = "ashby"

    def fetch(self, company: str, board_token: str, client: httpx.Client) -> list[RawJob]:
        data = get_json(client, f"https://api.ashbyhq.com/posting-api/job-board/{board_token}")
        out = []
        for j in data.get("jobs", []):
            if j.get("isListed") is False:
                continue
            addr = ((j.get("address") or {}).get("postalAddress") or {})
            loc = j.get("location", "") or ""
            extra = [s.get("location", "") if isinstance(s, dict) else str(s) for s in j.get("secondaryLocations", []) or []]
            out.append(RawJob(
                source=self.name, external_id=j.get("id", ""), title=j.get("title", ""), company=company,
                url=j.get("jobUrl", "") or j.get("applyUrl", ""),
                location="; ".join(x for x in [loc, *extra] if x),
                description_html=j.get("descriptionHtml", ""), description_text=j.get("descriptionPlain", ""),
                posted_at=parse_dt(j.get("publishedAt")),
                remote_flag=True if j.get("isRemote") or j.get("workplaceType") == "Remote" else None,
                country=addr.get("addressCountry", "") or "",
            ))
        return out
