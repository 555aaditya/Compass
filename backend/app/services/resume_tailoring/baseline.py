"""Deterministic baseline tailoring of a copy of the master: remove disputed skills, reorder by relevance.

It never invents content and never edits the master. Rewriting bullets is left to a Claude Code session
guided by TAILOR.md, then validated by the same ATS and claim checks.
"""
from __future__ import annotations

import re

from app.services.job_matching.vocab import find_terms
from app.services.resume_tailoring import latex
from app.services.resume_tailoring.guard import ClaimGuard


def _is_disputed(item: str, guard: ClaimGuard) -> bool:
    low = item.lower()
    return any(re.search(rf"(?<![\w]){re.escape(lit)}(?![\w])", low) for lit in guard.literals)


def tailor_skills(tex: str, job_terms: set[str], guard: ClaimGuard) -> tuple[str, list[str]]:
    secs = [s for s in latex.sections(tex) if s.name.lower() in ("skills", "technical skills")]
    if not secs:
        return tex, []
    sec, notes = secs[0], []
    new_body = sec.body
    for m in list(latex.SKILL_LINE.finditer(sec.body)):
        label, items = m.group(2), [x.strip() for x in m.group(3).split(",") if x.strip()]
        kept = []
        for it in items:
            if _is_disputed(it, guard):
                notes.append(f"Removed '{it}' from {label}: {guard.check(it)[0].reason if guard.check(it) else 'disputed in wiki'}")
            else:
                kept.append(it)
        kept.sort(key=lambda it: 0 if find_terms(it) & job_terms else 1)  # stable: JD matches first
        if kept != items:
            line = f"{m.group(1)}{', '.join(kept)}{m.group(4)}"
            new_body = new_body.replace(m.group(0), line)
    return tex[:sec.start] + tex[sec.start:sec.end].replace(sec.body, new_body) + tex[sec.end:], notes


def reorder_projects(tex: str, job_terms: set[str]) -> tuple[str, list[str]]:
    secs = [s for s in latex.sections(tex) if s.name.lower() == "projects"]
    if not secs:
        return tex, []
    sec = secs[0]
    blocks = latex.project_blocks(sec.body)
    if len(blocks) < 2:
        return tex, []
    # \newpage between projects forces a page break; drop it so reordering cannot strand a heading
    clean = [re.sub(r"\n\\newpage\s*\n", "\n", b) for b in blocks]
    scored = [(len(find_terms(b) & job_terms), i, b) for i, b in enumerate(clean)]
    ordered = [b for _, _, b in sorted(scored, key=lambda x: (-x[0], x[1]))]
    notes = []
    if [i for _, i, _ in sorted(scored, key=lambda x: (-x[0], x[1]))] != list(range(len(blocks))):
        notes.append("Reordered projects by overlap with the job's requirements")
    if clean != blocks:
        notes.append(r"Removed a hard \newpage between projects so page breaks flow naturally")
    head = sec.body[:sec.body.find(blocks[0])]
    tail = sec.body[sec.body.find(blocks[-1]) + len(blocks[-1]):]
    new_body = head + "".join(ordered) + tail
    return tex[:sec.start] + tex[sec.start:sec.end].replace(sec.body, new_body) + tex[sec.end:], notes


def baseline_resume(master_tex: str, job_terms: set[str], guard: ClaimGuard) -> tuple[str, list[str]]:
    tex, n1 = tailor_skills(master_tex, job_terms, guard)
    tex, n2 = reorder_projects(tex, job_terms)
    return tex, n1 + n2
