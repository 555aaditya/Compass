"""Per-job resume workspace: resumes/generated/<company>/<job_id>/. Paths are validated, never user-built."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from app.models import Job

FILES = ["resume.tex", "resume.pdf", "changes.md", "job_context.json", "match_analysis.json", "ats_report.json",
         "ats_report.md", "extracted_resume.txt"]


def safe_slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "x"


def job_dir(root: Path, job: Job) -> Path:
    root = root.resolve()
    d = (root / safe_slug(job.company.name) / str(job.id)).resolve()
    if root not in d.parents:
        raise ValueError("resume path escapes the generated resumes directory")
    return d


def verify_master(master: Path) -> str:
    """Return the master's sha256 and fail if it diverges from the imported manifest (tamper/overwrite guard)."""
    if not master.is_file():
        raise FileNotFoundError(f"Master resume not found at {master}. Run scripts/import_master.py <main.tex>.")
    digest = hashlib.sha256(master.read_bytes()).hexdigest()
    manifest = master.parent / "manifest.json"
    if manifest.exists():
        expected = json.loads(manifest.read_text()).get("files", {}).get(master.name)
        if expected and expected != digest:
            raise RuntimeError("Master resume changed since import. Re-run scripts/import_master.py if that was intended.")
    return digest


TAILOR_TEMPLATE = """# Tailor this resume (Claude Code session instructions)

You are tailoring a copy of the candidate's master LaTeX resume for ONE job. Work only inside this folder.

## Hard rules
1. Edit **resume.tex only**. Never touch `resumes/master/`. Never submit any application.
2. **Truthful only.** Every claim must be supported by `evidence_pack.md` or the wiki pages it links. Never invent
   skills, metrics, projects, ratings, publications or responsibilities.
3. Skills with status `missing` or `do_not_claim` in `keyword_matrix.json` must NOT appear. If the job wants them, leave the gap.
4. Do not reuse any phrase listed under "Claims that must not appear" below.
5. Use the job's exact terminology only where it accurately describes real work. No keyword stuffing, no hidden text.
6. Keep the ATS-friendly single-column layout and standard headings (Education, Skills, Experience, Projects, ...).
7. Bullets: Action + technical implementation + context + documented result. No invented numbers.

## What to do
- Read `job_context.json`, `match_analysis.json`, `keyword_matrix.json` and `evidence_pack.md`.
- Choose and order the 2-3 most relevant projects and the strongest experience bullets for this role.
  Recommended emphasis: **{emphasis}**
- Rewrite bullets from the wiki's tagged bullet bank where that makes the match clearer.
- Add an achievements line (e.g. LeetCode) only if it is relevant to this job.
- Save the file, then run:  `python scripts/resume.py finalize {job_id}`  from the repo root, and read `ats_report.md` and `changes.md`.

## Claims that must not appear (from the candidate's own wiki audit)
{claims}

## Job
{title} at {company}: {url}
"""


def evidence_pack(wiki_root: Path, analysis: dict, profile_disputed: list[dict]) -> str:
    parts = ["# Evidence pack", "", "Only the following wiki-backed evidence may be used. Paths are relative to the wiki root.", ""]
    paths = []
    for p in analysis.get("relevant_projects", []):
        paths.append(p["path"])
    paths.append("experience/oaknorth.md")
    for a in analysis.get("relevant_achievements", []):
        paths.append(a["path"])
    seen = set()
    for rel in paths:
        if rel in seen:
            continue
        seen.add(rel)
        f = (wiki_root / rel)
        if not f.is_file() or wiki_root.resolve() not in f.resolve().parents:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        parts += [f"## Source: {rel}", ""]
        picked = False
        for m in re.finditer(r"^##\s+(Resume bullets|JD keywords|Numbers|Role summary lines.*|Bullet bank.*|Claims to NOT make)\s*$",
                             text, re.M | re.I):
            end = re.search(r"^##\s", text[m.end():], re.M)
            parts += [text[m.start(): m.end() + (end.start() if end else len(text))].strip(), ""]
            picked = True
        if not picked:
            parts += [text[:3000], ""]
    parts += ["## Disputed claims (never use)", ""]
    parts += [f"- {d['name']}: {d.get('description') or d.get('evidence') or ''}" for d in profile_disputed]
    return "\n".join(parts) + "\n"
