"""Requirement extraction from a job description: which skills are required vs preferred."""
import re
from dataclasses import dataclass

from app.services.job_matching.vocab import CATEGORY, TERMS

REQUIRED_HEAD = re.compile(r"requirements?|qualifications?|what you['’]?ll (?:need|bring)|must[\s-]have|you have|"
                           r"basic qualifications|minimum|who you are|skills|about you|what we['’]?re looking for", re.I)
PREFERRED_HEAD = re.compile(r"preferred|nice[\s-]to[\s-]have|bonus|good to have|plus|desired|"
                            r"extra credit|ideally", re.I)
RESP_HEAD = re.compile(r"responsibilit|what you['’]?ll (?:do|work)|the role|day[\s-]to[\s-]day|your impact|you will", re.I)


@dataclass
class Requirement:
    term: str
    category: str
    priority: str  # required | preferred | mentioned


def _mode_for(line: str, current: str) -> str:
    stripped = line.strip().strip("*#:_ ").strip()
    if not stripped or len(stripped) > 80 or stripped.startswith("-"):
        return current
    if PREFERRED_HEAD.search(stripped):
        return "preferred"
    if RESP_HEAD.search(stripped):
        return "responsibilities"
    if REQUIRED_HEAD.search(stripped):
        return "required"
    return current


def extract_requirements(title: str, description: str) -> list[Requirement]:
    found: dict[str, str] = {}
    rank = {"mentioned": 0, "preferred": 1, "required": 2}
    mode = "neutral"
    for line in description.splitlines():
        new_mode = _mode_for(line, mode)
        is_heading = new_mode != mode or (len(line.strip()) < 80 and line.strip().endswith(":"))
        mode = new_mode
        for term, (_, rx) in TERMS.items():
            if rx.search(line):
                if mode == "required":
                    pr = "required"
                elif mode == "preferred" or re.search(r"\b(preferred|nice to have|bonus|a plus)\b", line, re.I):
                    pr = "preferred"
                else:
                    pr = "mentioned"
                if rank[pr] > rank.get(found.get(term, ""), -1):
                    found[term] = pr
        del is_heading
    for term, (_, rx) in TERMS.items():
        if rx.search(title):
            found[term] = "required"
    return [Requirement(t, CATEGORY[t], p) for t, p in sorted(found.items())]
