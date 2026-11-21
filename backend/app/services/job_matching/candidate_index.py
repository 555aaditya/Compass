"""Index of the candidate's evidenced skills, built only from candidate_profile (never product context)."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.job_matching.vocab import find_terms

SKILL_CATEGORIES = {"programming_languages", "frameworks", "libraries", "databases", "cloud_and_devops",
                    "data_engineering", "computer_science_fundamentals"}
LEVEL_TO_STATUS = {"deep": "demonstrated", "used": "practically_used", "touched": "familiar"}
STATUS_RANK = {"demonstrated": 3, "practically_used": 2, "familiar": 1}


@dataclass
class TermEvidence:
    status: str
    sources: list[dict] = field(default_factory=list)  # {name, path, url}


@dataclass
class CandidateIndex:
    terms: dict[str, TermEvidence] = field(default_factory=dict)
    disputed: dict[str, str] = field(default_factory=dict)
    projects: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    competitive: list[dict] = field(default_factory=list)
    research: list[dict] = field(default_factory=list)
    achievements: list[dict] = field(default_factory=list)

    def status(self, term: str) -> str:
        if term in self.terms:
            return self.terms[term].status
        return "do_not_claim" if term in self.disputed else "missing"

    @classmethod
    def from_profile(cls, profile: dict[str, list[dict]]) -> "CandidateIndex":
        idx = cls()

        def add(term: str, status: str, item: dict) -> None:
            cur = idx.terms.get(term)
            src = {"name": item["name"], "path": item["source_path"], "url": item.get("source_url", "")}
            if cur is None:
                idx.terms[term] = TermEvidence(status, [src])
                return
            if STATUS_RANK[status] > STATUS_RANK[cur.status]:
                cur.status = status
            cur.sources.append(src)

        for cat in SKILL_CATEGORIES:
            for item in profile.get(cat, []):
                status = LEVEL_TO_STATUS.get(item.get("level", ""))
                if not status or item.get("verification") == "unverified":
                    continue
                for t in find_terms(item["name"]):
                    add(t, status, item)
        for item in profile.get("projects", []):
            idx.projects.append(item)
            stack = " ".join(item.get("extra", {}).get("stack", []))
            for t in find_terms(stack):
                if t not in idx.terms:
                    add(t, "practically_used", item)
                else:
                    idx.terms[t].sources.append({"name": item["name"], "path": item["source_path"],
                                                 "url": item.get("source_url", "")})
        for d in profile.get("disputed_claims", []):
            for t in find_terms(d["name"]):
                idx.disputed.setdefault(t, d["name"])
        # a term with real skills-table evidence is not disputed
        for t in list(idx.disputed):
            if t in idx.terms and idx.terms[t].status != "familiar":
                del idx.disputed[t]
        idx.experience = profile.get("experience", [])
        idx.competitive = profile.get("competitive_programming", [])
        idx.research = profile.get("research_and_publications", [])
        idx.achievements = profile.get("achievements", []) + profile.get("certifications", [])
        return idx
