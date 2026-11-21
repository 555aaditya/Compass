from datetime import datetime, timezone

import httpx

from app.services.job_discovery.base import RawJob, get_json


class LeverAdapter:
    name = "lever"

    def fetch(self, company: str, board_token: str, client: httpx.Client) -> list[RawJob]:
        data = get_json(client, f"https://api.lever.co/v0/postings/{board_token}", params={"mode": "json"})
        out = []
        for j in data:
            cats = j.get("categories") or {}
            created = j.get("createdAt")
            wt = (j.get("workplaceType") or "").lower()
            text = j.get("descriptionPlain", "")
            for lst in j.get("lists", []) or []:
                text += f"\n\n{lst.get('text', '')}\n" + lst.get("content", "")
            out.append(RawJob(
                source=self.name, external_id=j.get("id", ""), title=j.get("text", ""), company=company,
                url=j.get("hostedUrl", ""), location=cats.get("location", "") or "",
                description_html=j.get("description", ""), description_text=text.strip(),
                posted_at=datetime.fromtimestamp(created / 1000, tz=timezone.utc) if created else None,
                remote_flag=True if wt == "remote" else None, country=j.get("country", "") or "",
            ))
        return out
