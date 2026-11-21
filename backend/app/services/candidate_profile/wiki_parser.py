"""Parse the Resume Wiki (markdown) into structured evidence records.

Pure functions, no database access. Content is treated as untrusted text: it is only
ever parsed, never executed or used as instructions.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

DEPTH = {"●●●": "deep", "●●": "used", "●": "touched"}

# Pages that are never candidate evidence.
SKIP_DIRS = {"claude-memory", "readme-gaps"}
SKIP_PREFIXES = ("scratch",)
SKIP_FILES = {"README.md", "_TEMPLATE.md"}

CATEGORY_HINTS = [
    ("competitive_programming", ("competitive", "codeforces", "leetcode", "atcoder", "dsa")),
    ("research_and_publications", ("paper", "research", "publication", "arxiv")),
    ("certifications", ("certif",)),
    ("achievements", ("award", "hackathon", "achievement")),
]

SKILL_SECTION_CATEGORY = {
    "languages": "programming_languages",
    "backend": "frameworks",
    "frontend": "frameworks",
    "ml / ai": "libraries",
    "ml and ai": "libraries",
    "data": "data_engineering",
    "databases": "databases",
    "cloud": "cloud_and_devops",
    "devops": "cloud_and_devops",
    "security": "cloud_and_devops",
    "testing": "computer_science_fundamentals",
    "algorithms": "computer_science_fundamentals",
}


@dataclass
class Evidence:
    category: str
    name: str
    description: str = ""
    level: str = ""
    evidence: str = ""
    source_path: str = ""
    verification: str = "verified"
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return claim_key(self.category, self.name)


def claim_key(category: str, name: str) -> str:
    norm = re.sub(r"\s+", " ", name.strip().lower())
    return hashlib.sha256(f"{category}|{norm}".encode()).hexdigest()[:32]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_candidate_page(rel: str, product_context: set[str]) -> bool:
    p = Path(rel)
    if rel in product_context or p.suffix != ".md" or p.name in SKIP_FILES:
        return False
    if any(part in SKIP_DIRS or part.startswith(SKIP_PREFIXES) for part in p.parts):
        return False
    return True


def parse_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta: dict = {}
    for line in text[3:end].splitlines():
        if ":" not in line or line.startswith((" ", "#")):
            continue
        k, v = line.split(":", 1)
        v = re.sub(r"\s+#.*$", "", v).strip()
        if v.startswith("[") and v.endswith("]"):
            meta[k.strip()] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
        else:
            meta[k.strip()] = v.strip("\"'")
    return meta, text[end + 4:].lstrip("\n")


def split_sections(body: str) -> dict[str, str]:
    """Map H2 heading -> section text."""
    sections: dict[str, list[str]] = {}
    cur = ""
    for line in body.splitlines():
        m = re.match(r"^##\s+(.*)", line)
        if m:
            cur = m.group(1).strip()
            sections[cur] = []
        elif cur:
            sections[cur].append(line)
    return {k: "\n".join(v) for k, v in sections.items()}


def parse_table(text: str) -> list[dict[str, str]]:
    rows = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(rows) < 3:
        return []
    cells = lambda ln: [c.strip() for c in ln.strip().strip("|").split("|")]  # noqa: E731
    head = [h.lower() for h in cells(rows[0])]
    out = []
    for ln in rows[2:]:
        c = cells(ln)
        if len(c) >= len(head):
            out.append(dict(zip(head, c)))
    return out


def strip_md(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    return re.sub(r"[*`]", "", s).strip()


def link_target(s: str) -> str:
    m = re.search(r"\]\(([^)]+)\)", s)
    return m.group(1) if m else ""


def needs_verification(text: str) -> bool:
    return "(verify)" in text.lower()


def skill_literals(name: str) -> list[str]:
    """'Spark / PySpark' -> ['Spark', 'PySpark']; 'Hive / Hadoop' -> ['Hive', 'Hadoop']."""
    name = re.sub(r"\([^)]*\)", "", name)
    return [x.strip() for x in re.split(r"\s*/\s*|,", name) if x.strip()]


def parse_skills(text: str, path: str) -> list[Evidence]:
    out: list[Evidence] = []
    for heading, body in split_sections(text).items():
        h = heading.lower()
        if h.startswith("do not list"):
            for row in parse_table(body):
                name = strip_md(next(iter(row.values())))
                out.append(Evidence(
                    "disputed_claims", name,
                    description=strip_md(row.get("reality", "")),
                    evidence=strip_md(row.get("action", "")), source_path=path,
                    verification="disputed",
                    extra={"kind": "skill", "literals": skill_literals(name)},
                ))
            continue
        cat = next((v for k, v in SKILL_SECTION_CATEGORY.items() if h.startswith(k)), None)
        if not cat:
            continue
        for row in parse_table(body):
            name = strip_md(row.get("skill", ""))
            depth = DEPTH.get(row.get("depth", "").strip(), "")
            if not name or not depth:
                continue
            ev = row.get("evidence", "")
            out.append(Evidence(
                cat, name, level=depth, evidence=strip_md(ev), source_path=path,
                verification="unverified" if needs_verification(ev) else "verified",
                extra={"section": heading},
            ))
    return out


def parse_profile(text: str, path: str) -> list[Evidence]:
    out: list[Evidence] = []
    sections = split_sections(text)
    for row in parse_table(sections.get("Links", "")):
        use = strip_md(row.get("use", ""))
        out.append(Evidence("contact", use, description=strip_md(row.get("link", "")),
                            source_path=path, extra={"url": link_target(row.get("link", ""))}))
    for row in parse_table(sections.get("Education", "")):
        inst = strip_md(row.get("institution", ""))
        out.append(Evidence(
            "education", inst, description=strip_md(row.get("qualification", "")),
            evidence=f"{row.get('score', '')}; {row.get('years', '')}", source_path=path,
            extra={"score": row.get("score", ""), "years": row.get("years", "")},
        ))
    return out


def parse_project(text: str, path: str) -> list[Evidence]:
    meta, body = parse_front_matter(text)
    title = meta.get("title") or Path(path).stem.replace("-", " ").title()
    summary = ""
    for line in body.splitlines():
        if line.startswith(">"):
            summary = re.sub(r"^>\s*(\[![a-z]+\]\s*)?", "", line).strip()
            break
    flagged = needs_verification(text) or "⚠" in text
    base_extra = {
        "repo": meta.get("repo", ""), "period": meta.get("period", ""),
        "status": meta.get("status", ""), "type": meta.get("type", ""),
        "domains": meta.get("domains", []), "stack": meta.get("stack", []),
        "strength": meta.get("resume_strength", "")[:1],
    }
    out = [Evidence("projects", strip_md(title), description=strip_md(summary),
                    evidence=meta.get("repo", ""), source_path=path,
                    verification="verified", extra={**base_extra, "has_open_caveats": flagged})]
    low = path.lower()
    for cat, hints in CATEGORY_HINTS:
        if any(h in low for h in hints):
            out.append(Evidence(cat, strip_md(title), description=strip_md(summary),
                                evidence=meta.get("repo", ""), source_path=path,
                                extra=base_extra))
            break
    return out


def parse_experience(text: str, path: str) -> list[Evidence]:
    meta, body = parse_front_matter(text)
    sections = split_sections(body)
    title_m = re.search(r"^#\s+(.*)", body, re.M)
    title = strip_md(title_m.group(1)) if title_m else Path(path).stem
    out = [Evidence("experience", title, source_path=path,
                    description=strip_md(next((v for v in body.splitlines() if v.startswith(">")), "")).lstrip("> "))]
    for heading, sec in sections.items():
        if heading.lower().startswith("claims to not make"):
            for line in sec.splitlines():
                m = re.match(r"^- \*\*(.+?)\*\*\s*(.*)", line)
                if m:
                    quoted = re.findall(r'"([^"]{4,})"', m.group(1)) or [strip_md(m.group(1)).strip('".')]
                    out.append(Evidence("disputed_claims", quoted[0].strip(), description=strip_md(m.group(2)),
                                        source_path=path, verification="disputed",
                                        extra={"phrases": [q.strip() for q in quoted], "kind": "claim"}))
    return out


def parse_generic(text: str, path: str) -> list[Evidence]:
    """Future pages (papers, certifications, ratings ...). Category from front matter or path."""
    meta, body = parse_front_matter(text)
    title_m = re.search(r"^#\s+(.*)", body, re.M)
    title = meta.get("title") or (strip_md(title_m.group(1)) if title_m else Path(path).stem)
    cat = meta.get("category", "")
    if not cat:
        low = path.lower()
        cat = next((c for c, hints in CATEGORY_HINTS if any(h in low for h in hints)), "")
    ambiguous = not cat
    cat = cat or "other"
    summary = next((strip_md(ln.lstrip("> ")) for ln in body.splitlines() if ln.startswith(">")), "")
    return [Evidence(cat, strip_md(title), description=summary, source_path=path,
                     verification="unverified" if ambiguous or needs_verification(text) else "verified",
                     extra={"meta": meta, "ambiguous_category": ambiguous})]


def parse_audit(text: str, path: str) -> list[Evidence]:
    """Rows of resume-audit.md judged Wrong or Unbacked become disputed claims (never candidate skills)."""
    out: list[Evidence] = []
    for heading, body in split_sections(text).items():
        for row in parse_table(body):
            line = row.get("resume line") or row.get("listed") or ""
            verdict = strip_md(row.get("verdict", "")).lower()
            if verdict not in ("wrong", "unbacked"):
                continue
            quoted = re.findall(r'"([^"]{4,})"', line)
            fix = strip_md(row.get("evidence and fix", ""))
            name = strip_md(line)[:200]
            out.append(Evidence("disputed_claims", f"{heading}: {name}", description=fix, source_path=path,
                                verification="disputed",
                                extra={"phrases": quoted, "kind": "audit", "verdict": verdict,
                                       "terms": [] if quoted else [strip_md(line)]}))
    return out


def parse_page(rel: str, text: str) -> list[Evidence]:
    p = Path(rel)
    if p.name == "resume-audit.md":
        return parse_audit(text, rel)
    if p.name == "skills.md":
        return parse_skills(text, rel)
    if p.name == "profile.md":
        return parse_profile(text, rel)
    if p.parts[0] == "projects":
        return parse_project(text, rel)
    if p.parts[0] == "experience":
        return parse_experience(text, rel)
    return parse_generic(text, rel)
