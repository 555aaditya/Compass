"""Deterministic hard filters. An LLM never overrides these."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.services.job_matching.preferences import Preferences

SENIOR_RE = re.compile(
    r"\b(senior|sr\.?|(?<!technical )staff|principal|lead|manager|director|head of|vp|vice president|architect|"
    r"distinguished|fellow|sde[\s-]*(?:iii|3|iv|4)|sde[\s-]*ii\b|sde[\s-]*2|engineer\s*(?:iii|iv|ii)\b|level\s*[3-9])\b", re.I)
NON_TECH_RE = re.compile(
    r"\b(sales|marketing|recruit\w*|talent|account (?:executive|manager)|customer success|support specialist|"
    r"legal|counsel|finance|accountant|payroll|hr |human resources|people partner|designer|writer|"
    r"business development|executive|user research|\\bux\\b|researcher|operations manager|office|executive assistant|content|seo|social media|"
    r"product manager|program manager|analyst relations|solutions? consultant)\b", re.I)
NON_SWE_RE = re.compile(
    r"\b(customer success|customer support|technical support|cloud support|support (?:engineer|specialist|analyst)|"
    r"sales engineer|solutions? (?:engineer|architect|consultant)|professional services|technical account|"
    r"implementation (?:engineer|consultant|specialist)|field engineer|pre[\s-]?sales|forward deployed account)\b", re.I)
TECH_TERMS_RE = re.compile(r"\b(engineer|engineering|developer|sde|sdet|software|programmer|devops|sre|data|ml|ai|"
                           r"research|scientist|platform|backend|back-end|frontend|front-end|full[\s-]?stack|"
                           r"member of technical staff|swe|mts|security|qa|automation)\b", re.I)
FRESHER_RE = re.compile(r"\b(fresher|freshers|new[\s-]?grad(?:uate)?s?|recent graduate|entry[\s-]?level|"
                        r"graduate|campus|early career|0\s*(?:-|–|to)\s*[12]\s*years?|no experience required|intern)\b", re.I)
YEARS_RE = re.compile(
    r"(\d{1,2})\s*(?:\+|\bplus\b)?\s*(?:(?:-|–|to)\s*(\d{1,2})\s*)?\+?\s*years?(?:['’]s)?\s*(?:of\s+)?"
    r"(?:\w+\s+){0,4}?(?:experience|exp\b)", re.I)
UNPAID_RE = re.compile(r"\b(unpaid|volunteer|no stipend|without (?:pay|compensation))\b", re.I)
FOREIGN_RE = re.compile(
    r"\b(united states|usa|us|u\.s\.|us only|us-based|canada|united kingdom|uk|london|germany|berlin|france|paris|"
    r"ireland|dublin|poland|warsaw|singapore|hong kong|australia|sydney|new zealand|brazil|mexico|japan|tokyo|"
    r"china|israel|netherlands|amsterdam|spain|portugal|dubai|uae|emea|latam|nyc|new york|san francisco|seattle|"
    r"austin|boston|toronto|vancouver|bay area|europe|north america|washington|d\.c\.|chicago|atlanta|denver|texas|"
    r"california|colorado|virginia|massachusetts|egypt|cairo|saudi|ksa|riyadh|kenya|nigeria|south africa|turkey|"
    r"philippines|manila|indonesia|jakarta|vietnam|thailand|bangkok|korea|seoul|taiwan|malaysia|kuala lumpur)\b", re.I)
REMOTE_RE = re.compile(r"\bremote\b|\bwork from (?:home|anywhere)\b|\banywhere\b", re.I)
ANYWHERE_RE = re.compile(r"\b(remote[\s,-]*(?:anywhere|worldwide|global|apac)|work from anywhere|"
                         r"anywhere in the world|worldwide)\b", re.I)
HYBRID_RE = re.compile(r"\bhybrid\b", re.I)


@dataclass
class Eligibility:
    status: str = "eligible"  # eligible | uncertain | rejected
    reasons: list[str] = field(default_factory=list)
    rejections: list[str] = field(default_factory=list)
    work_mode: str = "unknown"
    experience_min: float | None = None
    experience_max: float | None = None
    location_ok: str = "uncertain"  # yes | uncertain | no
    is_fresher_friendly: bool = False

    def reject(self, why: str) -> None:
        self.status = "rejected"
        self.reasons.append(why)
        self.rejections.append(why)

    def flag(self, why: str) -> None:
        if self.status == "eligible":
            self.status = "uncertain"
        self.reasons.append(why)


def parse_experience(text: str) -> tuple[float | None, float | None]:
    """Return (min_years, max_years) from the strictest 'N+ years of experience' style phrase."""
    mins, maxs = [], []
    for m in YEARS_RE.finditer(text):
        lo = float(m.group(1))
        hi = float(m.group(2)) if m.group(2) else None
        if lo > 30:
            continue
        mins.append(lo)
        maxs.append(hi if hi is not None else lo)
    if not mins:
        return None, None
    return max(mins), max(maxs)


def detect_work_mode(location: str, description: str, remote_flag: bool | None) -> str:
    blob = f"{location} {description[:1500]}"
    if remote_flag or re.search(r"\(remote\)|\bremote\b", location, re.I):
        return "remote"
    if HYBRID_RE.search(blob):
        return "hybrid"
    if REMOTE_RE.search(location):
        return "remote"
    return "onsite" if location.strip() else "unknown"


def check_location(location: str, description: str, mode: str, prefs: Preferences, country: str = "") -> tuple[str, str]:
    loc = f"{location} {country}".lower()
    india_terms = prefs.india_locations
    in_india = any(re.search(rf"\b{re.escape(t)}\b", loc) for t in india_terms)
    if in_india:
        return "yes", "India location"
    if mode == "remote":
        m = re.search(r"remote\s*[-–—,:(/]\s*([a-z][a-z .&]+)", loc)
        if m and not re.search(r"india|anywhere|global|worldwide|apac|asia|any\b|all\b", m.group(1)):
            return "no", f"Remote restricted to another region: '{location}'"
        if FOREIGN_RE.search(loc) and not ANYWHERE_RE.search(f"{location} {description[:3000]}"):
            return "no", f"Remote restricted to another region: '{location}'"
        if re.search(r"\bindia\b", description[:3000], re.I) and re.search(r"remote", description[:3000], re.I):
            return "yes", "Remote; description mentions India"
        if ANYWHERE_RE.search(f"{location} {description[:3000]}"):
            return "yes", "Remote anywhere / worldwide"
        if FOREIGN_RE.search(loc):
            return "no", f"Remote restricted to another region: '{location}'"
        return "uncertain", "Remote but eligibility for India not stated"
    if not location.strip():
        return "uncertain", "No location given"
    return "no", f"Location outside India: '{location}'"


def evaluate(title: str, location: str, description: str, posted_at: datetime | None, prefs: Preferences,
             remote_flag: bool | None = None, country: str = "", now: datetime | None = None) -> Eligibility:
    now = now or datetime.now(timezone.utc)
    e = Eligibility()
    blob = f"{title}\n{description}"

    # seniority
    if SENIOR_RE.search(title):
        e.reject(f"Seniority in title: '{title}'")
    # non-technical
    if NON_SWE_RE.search(title):
        e.reject("Customer-facing / support role, not software engineering")
    elif NON_TECH_RE.search(title) and not re.search(r"\b(engineer|developer|sde|software)\b", title, re.I):
        e.reject("Non-technical role")
    elif not TECH_TERMS_RE.search(title):
        e.reject("Title is not an engineering role")
    if UNPAID_RE.search(blob) and not prefs.allow_unpaid:
        e.reject("Unpaid role")

    # experience
    lo, hi = parse_experience(blob)
    e.experience_min, e.experience_max = lo, hi
    e.is_fresher_friendly = bool(FRESHER_RE.search(blob))
    if lo is not None and lo > prefs.max_experience_years:
        if e.is_fresher_friendly and lo <= prefs.max_experience_years + 1:
            e.flag(f"Asks {lo:g}+ years but also mentions freshers/graduates")
        else:
            e.reject(f"Requires {lo:g}+ years of experience (limit {prefs.max_experience_years:g})")
    elif lo is None:
        if e.is_fresher_friendly:
            e.experience_min = 0
        else:
            e.flag("Experience requirement not stated")

    # location
    e.work_mode = detect_work_mode(location, description, remote_flag)
    e.location_ok, why = check_location(location, description, e.work_mode, prefs, country)
    if e.location_ok == "no":
        e.reject(why)
    elif e.location_ok == "uncertain":
        e.flag(why)
    if re.search(r"\b(must|required to|willing to) relocate (?:to|outside)\b", blob, re.I) \
            and not prefs.allow_relocation_outside_india and e.location_ok != "yes":
        e.reject("Mandatory relocation outside India")

    # freshness
    if posted_at is not None:
        pa = posted_at if posted_at.tzinfo else posted_at.replace(tzinfo=timezone.utc)
        if (now - pa).days > prefs.freshness_days:
            e.reject(f"Older than {prefs.freshness_days}-day freshness window")
    return e
