"""Resume pipeline: prepare a workspace + baseline, then finalize (compile, validate, report) after editing."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import ATSReport, Job, ResumeVersion
from app.services.ats_analysis import diff as diff_mod, report as report_mod, validator
from app.services.candidate_profile.sync import export_profile
from app.services.job_matching.candidate_index import CandidateIndex
from app.services.job_matching.requirements import Requirement
from app.services.resume_tailoring import latex, workspace
from app.services.resume_tailoring.baseline import baseline_resume
from app.services.resume_tailoring.compile import compile_tex
from app.services.resume_tailoring.guard import ClaimGuard, load_overrides
from app.services.resume_tailoring.keyword_matrix import build_matrix


def _reqs(job: Job) -> list[Requirement]:
    return [Requirement(s.term, s.category, s.priority) for s in job.skills]


def _job_ctx(job: Job) -> dict:
    return {"job_id": job.id, "company": job.company.name, "title": job.title, "location": job.location,
            "work_mode": job.work_mode, "apply_url": job.apply_url, "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "experience_min": job.experience_min, "requirements": [{"term": s.term, "category": s.category, "priority": s.priority}
                                                                    for s in job.skills],
            "description": job.description}


def prepare_resume(db: Session, job: Job, s: Settings) -> ResumeVersion:
    master = s.master_resume_path
    workspace.verify_master(master)
    profile = export_profile(db)
    idx, guard = CandidateIndex.from_profile(profile), ClaimGuard(profile, load_overrides(s.claim_overrides_path))
    version = (db.scalar(select(ResumeVersion.version).where(ResumeVersion.job_id == job.id)
                         .order_by(ResumeVersion.version.desc())) or 0) + 1
    d = workspace.job_dir(s.generated_resumes_path, job)
    if d.exists():  # keep the previous version rather than overwrite it
        shutil.move(d, d.with_name(f"{d.name}.v{version - 1}"))
    d.mkdir(parents=True)
    matrix = build_matrix(_reqs(job), idx)
    job_terms = {r["requirement"] for r in matrix if r["status"] in ("demonstrated", "practically_used", "familiar")}
    master_tex = master.read_text(encoding="utf-8")
    tex, notes = baseline_resume(master_tex, job_terms, guard)
    (d / "resume.tex").write_text(tex, encoding="utf-8")
    for extra in master.parent.iterdir():  # assets / styles the master depends on
        if extra.is_file() and extra.suffix in {".sty", ".cls", ".png", ".jpg", ".jpeg", ".ttf", ".otf", ".bib"}:
            shutil.copy2(extra, d / extra.name)
    ctx = _job_ctx(job)
    (d / "job_context.json").write_text(json.dumps(ctx, indent=2))
    (d / "match_analysis.json").write_text(json.dumps({"score": job.score, "category": job.category,
                                                       "breakdown": job.score_breakdown, **job.analysis}, indent=2))
    (d / "keyword_matrix.json").write_text(json.dumps(matrix, indent=2))
    (d / "baseline_notes.json").write_text(json.dumps(notes, indent=2))
    disputed = profile.get("disputed_claims", [])
    (d / "evidence_pack.md").write_text(workspace.evidence_pack(s.wiki_path, job.analysis, disputed), encoding="utf-8")
    claims = "\n".join(f"- {p}" for d_ in disputed for p in (d_["extra"].get("phrases") or [])[:2]) or "- (none)"
    (d / "TAILOR.md").write_text(workspace.TAILOR_TEMPLATE.format(
        emphasis=job.analysis.get("recommended_emphasis", "strongest relevant projects"), job_id=job.id,
        claims=claims, title=job.title, company=job.company.name, url=job.apply_url))
    rv = ResumeVersion(job_id=job.id, version=version, directory=str(d), state="prepared")
    db.add(rv)
    if job.status in ("discovered", "shortlisted"):
        job.status = "resume_generated"
    db.commit()
    return rv


def finalize_resume(db: Session, rv: ResumeVersion, s: Settings, compiler: str | None = None) -> dict:
    d = Path(rv.directory)
    job = rv.job
    master = s.master_resume_path
    workspace.verify_master(master)
    master_tex = master.read_text(encoding="utf-8")
    tex = (d / "resume.tex").read_text(encoding="utf-8")
    profile = export_profile(db)
    guard = ClaimGuard(profile, load_overrides(s.claim_overrides_path))
    violations = [v.to_dict() for v in guard.check(latex.tex_to_text(tex))]
    notes = json.loads((d / "baseline_notes.json").read_text()) if (d / "baseline_notes.json").exists() else []
    (d / "changes.md").write_text(diff_mod.change_report(master_tex, tex, notes, violations), encoding="utf-8")

    res = compile_tex(d, "resume.tex", compiler)
    rv.compile_log = res.log
    compile_info = {"ok": res.ok, "compiler": res.compiler, "errors": res.errors or [],
                    "log_tail": res.log[-1500:] if not res.ok else ""}
    matrix = json.loads((d / "keyword_matrix.json").read_text())
    summary = {"state": "failed", "compile": compile_info, "violations": violations}
    if not res.ok:
        rv.state = "failed"
        (d / "ats_report.md").write_text("# ATS report\n\nCompilation failed, so no PDF checks ran.\n\n"
                                         f"```\n{res.log[-3000:]}\n```\n\n## Claim check\n\n"
                                         + "\n".join(f"- {v['severity']}: `{v['text']}`: {v['reason']}" for v in violations) + "\n")
        db.commit()
        return summary
    validation = validator.validate(tex, res.pdf)
    (d / "extracted_resume.txt").write_text(validation["extracted_text"], encoding="utf-8")
    rep = report_mod.build_report(
        job={"title": job.title, "company": job.company.name, "url": job.apply_url}, matrix=matrix,
        validation=validation, violations=violations, section_order=[x.name for x in latex.sections(tex)],
        compile_info={"ok": True, "compiler": res.compiler})
    (d / "ats_report.json").write_text(json.dumps(rep, indent=2))
    (d / "ats_report.md").write_text(report_mod.to_markdown(rep), encoding="utf-8")
    db.add(ATSReport(resume_id=rv.id, report=rep))
    rv.state = "compiled"
    if job.status in ("resume_generated", "shortlisted", "discovered"):
        job.status = "awaiting_approval" if s.require_resume_approval else "resume_generated"
    db.commit()
    return {"state": "compiled", "overall": validation["overall"], "violations": violations, "compile": compile_info}


class ApprovalBlocked(Exception):
    pass


def approve_resume(db: Session, rv: ResumeVersion, force: bool = False) -> ResumeVersion:
    if rv.state != "compiled":
        raise ApprovalBlocked("Resume has not compiled successfully; finalize it first.")
    rep = db.scalar(select(ATSReport).where(ATSReport.resume_id == rv.id).order_by(ATSReport.id.desc()))
    errs = [v for v in (rep.report.get("claim_violations", []) if rep else []) if v["severity"] == "error"]
    if errs and not force:
        raise ApprovalBlocked(f"{len(errs)} claim(s) contradict the wiki evidence: " + "; ".join(v["text"] for v in errs[:3]))
    rv.approved, rv.state = True, "approved"
    rv.created_at = rv.created_at or datetime.now(timezone.utc)
    db.commit()
    return rv
