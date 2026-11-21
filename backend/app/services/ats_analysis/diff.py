"""Change report between the master and a job-specific resume."""
from __future__ import annotations

import difflib

from app.services.resume_tailoring import latex


def change_report(master: str, tailored: str, notes: list[str], violations: list[dict]) -> str:
    mb, tb = latex.bullets(master), latex.bullets(tailored)
    ms, ts = [s.name for s in latex.sections(master)], [s.name for s in latex.sections(tailored)]
    added = [b for b in tb if b not in mb]
    removed = [b for b in mb if b not in tb]
    # a bullet that changed is shown as a rewrite when a close counterpart exists
    rewrites, pure_added = [], []
    for a in added:
        near = difflib.get_close_matches(a, removed, n=1, cutoff=0.5)
        if near:
            rewrites.append((near[0], a))
            removed.remove(near[0])
        else:
            pure_added.append(a)
    ms_skills = {i for s in latex.sections(master) if s.name.lower().endswith("skills")
                 for _, its in latex.skill_lines(s.body) for i in its}
    ts_skills = {i for s in latex.sections(tailored) if s.name.lower().endswith("skills")
                 for _, its in latex.skill_lines(s.body) for i in its}
    L = ["# Changes from master resume", ""]
    L += ["## Automatic changes", ""] + ([f"- {n}" for n in notes] or ["- none"])
    L += ["", "## Sections", "", f"- Master order: {', '.join(ms)}", f"- This resume: {', '.join(ts)}",
          "- Reordered: " + ("yes" if ms != ts else "no")]
    L += ["", "## Skills", "", f"- Removed: {', '.join(sorted(ms_skills - ts_skills)) or 'none'}",
          f"- Added: {', '.join(sorted(ts_skills - ms_skills)) or 'none'}"]
    L += ["", "## Bullets", "", f"- Added: {len(pure_added)}; rewritten: {len(rewrites)}; removed: {len(removed)}"]
    for old, new in rewrites:
        L += ["", f"- Rewritten:", f"  - before: {old}", f"  - after: {new}"]
    for b in pure_added:
        L += ["", f"- Added: {b}"]
    for b in removed:
        L += ["", f"- Removed: {b}"]
    L += ["", "## Unsupported or uncertain claims still present", ""]
    L += [f"- **{v['severity']}** `{v['text']}`: {v['reason']}" for v in violations] or ["- none"]
    L += ["", "## Unified diff", "", "```diff"]
    L += list(difflib.unified_diff(master.splitlines(), tailored.splitlines(), "master", "resume", lineterm="", n=1))
    L += ["```", ""]
    return "\n".join(L)
