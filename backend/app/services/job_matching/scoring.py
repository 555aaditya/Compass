"""Explainable job scoring. Hard filters come from eligibility.py and are not overridden here."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from app.services.job_matching.candidate_index import CandidateIndex
from app.services.job_matching.eligibility import Eligibility
from app.services.job_matching.preferences import Preferences
from app.services.job_matching.requirements import Requirement
from app.services.job_matching.vocab import find_terms

STRENGTH = {"demonstrated": 1.0, "practically_used": 0.8, "familiar": 0.45, "missing": 0.0, "do_not_claim": 0.0}
PRIORITY_WEIGHT = {"required": 3.0, "preferred": 1.5, "mentioned": 0.5}

FLAVORS = [
    ("ml", r"machine learning|\bml\b|\bai\b|llm|research|deep learning|nlp", "PyTorch, LLM, research and ML projects; research papers if present"),
    ("data", r"data engineer|etl|pipeline|warehouse|analytics engineer|spark|airflow", "SQL, Python, pipelines, Airflow/Kafka/Athena, data-heavy projects"),
    ("platform", r"platform|devops|sre|infrastructure|cloud|reliability", "Terraform, AWS, CI/CD, Docker, cloud infrastructure work"),
    ("backend", r"backend|back-end|api|server|python developer|java developer", "APIs, databases, auth, testing, backend projects"),
    ("fullstack", r"full[\s-]?stack|frontend|front-end|react|web developer", "React/TypeScript plus a backend, end-to-end shipped products"),
    ("devtools", r"developer tools|devtools|developer experience|compiler|sdk|tooling", "Rust/compiler and OSS tooling work"),
    ("sde", r"sde|software (?:development )?engineer|software developer|swe|member of technical staff", "DSA, language fluency, testing, strongest software projects, competitive programming"),
]


def classify_flavor(title: str, description: str) -> tuple[str, str]:
    for name, pat, emphasis in FLAVORS:
        if re.search(pat, title, re.I):
            return name, emphasis
    head = description[:800]
    for name, pat, emphasis in FLAVORS:
        if re.search(pat, head, re.I):
            return name, emphasis
    return "sde", FLAVORS[-1][2]


def role_relevance(title: str, prefs: Preferences) -> float:
    t = title.lower()
    hits = [r for r in prefs.target_roles if r in t]
    if not hits:
        return 0.35
    return 1.0 if any(h in ("software engineer", "sde", "software development engineer", "backend engineer",
                            "full stack", "data engineer", "python developer") for h in hits) else 0.85


def experience_fit(e: Eligibility, prefs: Preferences) -> float:
    if e.experience_min is None:
        return 0.5
    if e.experience_min <= 0 or e.is_fresher_friendly and e.experience_min <= 1:
        return 1.0
    if e.experience_min <= 1:
        return 0.95
    if e.experience_min <= prefs.max_experience_years:
        return 0.75
    return 0.2


def freshness_fit(posted_at: datetime | None, prefs: Preferences, now: datetime) -> float:
    if posted_at is None:
        return 0.6
    pa = posted_at if posted_at.tzinfo else posted_at.replace(tzinfo=timezone.utc)
    days = max((now - pa).days, 0)
    return max(0.0, 1 - days / max(prefs.freshness_days, 1))


def category_for(score: float) -> str:
    return "excellent" if score >= 85 else "strong" if score >= 70 else "moderate" if score >= 55 else "low"


def score_job(*, title: str, description: str, posted_at: datetime | None, reqs: list[Requirement],
              elig: Eligibility, idx: CandidateIndex, prefs: Preferences, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    w = prefs.weights
    weight_sum = sum(w.values()) or 1

    # skills
    matched, missing, blocked, num, den = [], [], [], 0.0, 0.0
    for r in reqs:
        pw = PRIORITY_WEIGHT[r.priority]
        st = idx.status(r.term)
        den += pw
        num += pw * STRENGTH[st]
        entry = {"term": r.term, "priority": r.priority, "status": st,
                 "evidence": [s["name"] for s in idx.terms[r.term].sources[:3]] if r.term in idx.terms else []}
        if st in ("demonstrated", "practically_used", "familiar"):
            matched.append(entry)
        else:
            (blocked if st == "do_not_claim" else missing).append(entry)
    skills_fit = num / den if den else 0.4

    # projects and achievements
    job_terms = {r.term for r in reqs}
    scored_projects = []
    for p in idx.projects + [e for e in idx.experience if e.get("extra", {}).get("stack_terms")]:
        ex = p.get("extra", {})
        pt = set(ex.get("stack_terms", [])) or find_terms(" ".join(ex.get("stack", [])) + " " + p["name"] + " " + p.get("description", ""))
        overlap = sorted(job_terms & pt)
        if overlap:
            strength = {"A": 1.0, "B": 0.7, "C": 0.4}.get(p.get("extra", {}).get("strength", ""), 0.5)
            scored_projects.append((len(overlap) * strength, p, overlap))
    scored_projects.sort(key=lambda x: -x[0])
    top = scored_projects[:3]
    proj_fit = min(1.0, sum(s for s, _, _ in top) / 4.0)
    flavor, emphasis = classify_flavor(title, description)
    algo = bool(re.search(r"algorithm|data structure|competitive|problem[\s-]solving|dsa", f"{title} {description}", re.I)) \
        or flavor == "sde"
    cp_rel = [c for c in idx.competitive] if algo else []
    research_rel = idx.research if flavor == "ml" else []
    if cp_rel:
        proj_fit = min(1.0, proj_fit + 0.2)
    if research_rel:
        proj_fit = min(1.0, proj_fit + 0.15)

    loc_fit = {"yes": 1.0, "uncertain": 0.5, "no": 0.0}[elig.location_ok]
    parts = {
        "skills": skills_fit * w["skills"], "role": role_relevance(title, prefs) * w["role"],
        "experience": experience_fit(elig, prefs) * w["experience"], "projects": proj_fit * w["projects"],
        "location": loc_fit * w["location"], "freshness": freshness_fit(posted_at, prefs, now) * w["freshness"],
    }
    total = round(sum(parts.values()) / weight_sum * 100, 1)
    if elig.status == "uncertain":
        total = min(total, 84.0)  # an uncertain eligibility can never read as 'excellent'

    why = []
    if matched:
        why.append("Matches " + ", ".join(m["term"] for m in matched[:6]))
    if top:
        why.append("Relevant work: " + ", ".join(p["name"].split(" (")[0] for _, p, _ in top))
    if elig.is_fresher_friendly:
        why.append("Open to freshers / early-career")
    weaknesses = [f"No evidence for required skill: {m['term']}" for m in missing if m["priority"] == "required"]
    weaknesses += [f"{b['term']} is required but is on your do-not-claim list" for b in blocked if b["priority"] == "required"]
    if elig.status == "uncertain":
        weaknesses += elig.reasons

    return {
        "score": total, "category": category_for(total), "breakdown": {k: round(v, 1) for k, v in parts.items()},
        "analysis": {
            "flavor": flavor, "matching_skills": matched, "missing_skills": missing, "blocked_skills": blocked,
            "relevant_projects": [{"name": p["name"], "path": p["source_path"], "url": p.get("source_url", ""),
                                   "overlap": ov} for _, p, ov in top],
            "relevant_achievements": [{"name": c["name"], "path": c["source_path"]} for c in cp_rel],
            "competitive_programming_relevance": bool(cp_rel),
            "research_relevance": bool(research_rel),
            "experience_compatibility": {"min": elig.experience_min, "max": elig.experience_max,
                                         "fresher_friendly": elig.is_fresher_friendly},
            "location_compatibility": {"status": elig.location_ok, "work_mode": elig.work_mode},
            "why_matches": why, "weaknesses": weaknesses, "recommended_emphasis": emphasis,
        },
    }
