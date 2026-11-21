"""REST API. Read-mostly; the only writes are user-driven (status, settings, approvals, manual runs)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Settings, get_db, get_settings
from app.models import (JOB_STATUSES, ATSReport, CandidateEvidence, Company, Job, Notification, ProfileSnapshot,
                        ResumeVersion, ScanHistory, WikiSyncHistory)
from app.services.applications.tracking import InvalidStatus, set_status
from app.services.candidate_profile.sync import export_profile
from app.services.job_matching.settings import load_preferences, save_preferences
from app.services.resume_tailoring import service as resume_service
from app.services.resume_tailoring.workspace import FILES
from app.workers import pipeline

router = APIRouter(prefix="/api")


def iso(d):
    """SQLite returns naive datetimes; they are stored in UTC, so label them so browsers don't read them as local."""
    from datetime import timezone
    return (d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d).isoformat()


def job_out(j: Job, full: bool = False) -> dict:
    out = {
        "id": j.id, "company": j.company.name, "title": j.title, "location": j.location, "work_mode": j.work_mode,
        "experience_min": j.experience_min, "score": j.score, "category": j.category, "status": j.status,
        "eligibility": j.eligibility, "eligibility_reasons": j.eligibility_reasons,
        "discovered_at": iso(j.first_seen_at), "posted_at": iso(j.posted_at) if j.posted_at else None,
        "source": j.sources[0].source if j.sources else None, "apply_url": j.apply_url, "active": j.active,
    }
    if full:
        out.update(description=j.description, notes=j.notes, analysis=j.analysis, score_breakdown=j.score_breakdown,
                   skills=[{"term": s.term, "category": s.category, "priority": s.priority} for s in j.skills],
                   sources=[{"source": s.source, "url": s.url} for s in j.sources])
    return out


def resume_out(r: ResumeVersion) -> dict:
    d = Path(r.directory)
    return {"id": r.id, "job_id": r.job_id, "company": r.job.company.name, "title": r.job.title, "score": r.job.score,
            "version": r.version, "state": r.state, "approved": r.approved, "created_at": iso(r.created_at),
            "files": [f for f in FILES if (d / f).is_file()]}


# ---- overview -------------------------------------------------------------
@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    count = lambda *w: db.scalar(select(func.count()).select_from(Job).where(*w)) or 0  # noqa: E731
    last_scan = db.scalar(select(ScanHistory).where(ScanHistory.status == "ok").order_by(ScanHistory.id.desc()))
    last_wiki = db.scalar(select(WikiSyncHistory).where(WikiSyncHistory.status == "ok").order_by(WikiSyncHistory.id.desc()))
    from datetime import datetime, timedelta, timezone
    week = datetime.now(timezone.utc) - timedelta(days=7)
    return {
        "total_jobs": count(), "new_jobs": count(Job.first_seen_at >= week),
        "excellent": count(Job.category == "excellent", Job.active.is_(True)),
        "strong": count(Job.category == "strong", Job.active.is_(True)),
        "shortlisted": count(Job.status == "shortlisted"), "applied": count(Job.status == "applied"),
        "interviews": count(Job.status == "interview"),
        "last_scan": {"at": iso(last_scan.finished_at), "new": last_scan.new_jobs} if last_scan and last_scan.finished_at else None,
        "last_wiki_sync": {"at": iso(last_wiki.finished_at), "pages": last_wiki.pages_seen} if last_wiki and last_wiki.finished_at else None,
        "recent_notifications": [{"job_id": n.job_id, "channel": n.channel, "status": n.status, "at": iso(n.sent_at)}
                                 for n in db.scalars(select(Notification).order_by(Notification.id.desc()).limit(5))],
    }


# ---- jobs -----------------------------------------------------------------
SORTS = {"score": Job.score.desc().nullslast(), "newest": Job.first_seen_at.desc(), "company": Company.name.asc(),
         "role": Job.title_norm.asc()}


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), min_score: float | None = None, company: str | None = None,
              work_mode: str | None = None, status: str | None = None, q: str | None = None,
              eligibility: str | None = None, max_experience: float | None = None, days: int | None = None,
              active_only: bool = True, sort: str = "score", limit: int = Query(100, le=500), offset: int = 0):
    stmt = select(Job).join(Company)
    if min_score is not None:
        stmt = stmt.where(Job.score >= min_score)
    if company:
        stmt = stmt.where(Company.name == company)
    if work_mode:
        stmt = stmt.where(Job.work_mode == work_mode)
    if status:
        stmt = stmt.where(Job.status == status)
    if eligibility:
        stmt = stmt.where(Job.eligibility == eligibility)
    if max_experience is not None:
        stmt = stmt.where(or_(Job.experience_min.is_(None), Job.experience_min <= max_experience))
    if q:
        stmt = stmt.where(or_(Job.title.ilike(f"%{q}%"), Job.location.ilike(f"%{q}%")))
    if days:
        from datetime import datetime, timedelta, timezone
        stmt = stmt.where(Job.first_seen_at >= datetime.now(timezone.utc) - timedelta(days=days))
    if active_only:
        stmt = stmt.where(Job.active.is_(True))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(SORTS.get(sort, SORTS["score"])).limit(limit).offset(offset)).all()
    return {"total": total, "items": [job_out(j) for j in rows]}


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "job not found")
    resumes = db.scalars(select(ResumeVersion).where(ResumeVersion.job_id == job_id).order_by(ResumeVersion.id.desc())).all()
    return {**job_out(j, True), "resumes": [resume_out(r) for r in resumes]}


class StatusIn(BaseModel):
    status: str
    note: str = ""


@router.post("/jobs/{job_id}/status")
def update_status(job_id: int, body: StatusIn, db: Session = Depends(get_db)):
    j = db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "job not found")
    try:
        set_status(db, j, body.status, body.note)
    except InvalidStatus as e:
        raise HTTPException(422, str(e)) from None
    return job_out(j, True)


@router.get("/statuses")
def statuses():
    return JOB_STATUSES


# ---- resumes --------------------------------------------------------------
@router.post("/jobs/{job_id}/resume")
def generate_resume(job_id: int, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    j = db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "job not found")
    try:
        return resume_out(resume_service.prepare_resume(db, j, s))
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(409, str(e)) from None


@router.get("/resumes")
def list_resumes(db: Session = Depends(get_db)):
    return [resume_out(r) for r in db.scalars(select(ResumeVersion).order_by(ResumeVersion.id.desc()))]


@router.post("/resumes/{rid}/finalize")
def finalize(rid: int, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    r = db.get(ResumeVersion, rid)
    if not r:
        raise HTTPException(404, "resume not found")
    return resume_service.finalize_resume(db, r, s)


class ApproveIn(BaseModel):
    force: bool = False


@router.post("/resumes/{rid}/approve")
def approve(rid: int, body: ApproveIn, db: Session = Depends(get_db)):
    r = db.get(ResumeVersion, rid)
    if not r:
        raise HTTPException(404, "resume not found")
    try:
        return resume_out(resume_service.approve_resume(db, r, body.force))
    except resume_service.ApprovalBlocked as e:
        raise HTTPException(409, str(e)) from None


@router.get("/resumes/{rid}/report")
def ats_report(rid: int, db: Session = Depends(get_db)):
    rep = db.scalar(select(ATSReport).where(ATSReport.resume_id == rid).order_by(ATSReport.id.desc()))
    if not rep:
        raise HTTPException(404, "no ATS report yet; finalize the resume first")
    return rep.report


@router.get("/resumes/{rid}/files/{name}")
def resume_file(rid: int, name: str, db: Session = Depends(get_db)):
    r = db.get(ResumeVersion, rid)
    if not r or name not in FILES:  # whitelist: no user-controlled path segments
        raise HTTPException(404, "file not found")
    f = Path(r.directory) / name
    if not f.is_file():
        raise HTTPException(404, "file not generated yet")
    return FileResponse(f, media_type="application/pdf" if name.endswith(".pdf") else "text/plain; charset=utf-8")


# ---- candidate profile ----------------------------------------------------
@router.get("/profile")
def profile(db: Session = Depends(get_db)):
    return export_profile(db)


@router.get("/profile/history")
def profile_history(db: Session = Depends(get_db)):
    return [{"id": r.id, "started_at": iso(r.started_at), "status": r.status, "pages_seen": r.pages_seen,
             "added": r.added, "modified": r.modified, "deleted": r.deleted, "warnings": r.warnings, "error": r.error}
            for r in db.scalars(select(WikiSyncHistory).order_by(WikiSyncHistory.id.desc()).limit(20))]


class VerifyIn(BaseModel):
    verification: str = Field(pattern="^(verified|unverified|disputed)$")


@router.post("/profile/evidence/{eid}/verification")
def set_verification(eid: int, body: VerifyIn, db: Session = Depends(get_db)):
    e = db.get(CandidateEvidence, eid)
    if not e:
        raise HTTPException(404, "evidence not found")
    e.verification = body.verification
    db.commit()
    return {"id": e.id, "verification": e.verification}


# ---- settings / companies / runs -----------------------------------------
@router.get("/settings")
def get_prefs(db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    return {"preferences": load_preferences(db).to_dict(), "environment": s.redacted()}


@router.put("/settings")
def put_prefs(body: dict, db: Session = Depends(get_db)):
    return save_preferences(db, body).to_dict()


class CompanyIn(BaseModel):
    name: str
    ats: str = Field(pattern="^(greenhouse|lever|ashby|manual)$")
    board_token: str = ""
    region: str = "global"
    priority: int = Field(5, ge=1, le=10)
    enabled: bool = True


@router.get("/companies")
def companies(db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name, "ats": c.ats, "board_token": c.board_token, "region": c.region,
             "priority": c.priority, "enabled": c.enabled, "last_ok_at": iso(c.last_ok_at) if c.last_ok_at else None,
             "last_error": c.last_error, "failures": c.consecutive_failures}
            for c in db.scalars(select(Company).order_by(Company.priority, Company.name))]


@router.post("/companies")
def add_company(body: CompanyIn, db: Session = Depends(get_db)):
    from app.services.job_discovery.store import slugify
    if db.scalar(select(Company).where(Company.name == body.name)):
        raise HTTPException(409, "company already exists")
    c = Company(slug=slugify(body.name), **body.model_dump())
    db.add(c)
    db.commit()
    return {"id": c.id}


@router.patch("/companies/{cid}")
def patch_company(cid: int, body: dict, db: Session = Depends(get_db)):
    c = db.get(Company, cid)
    if not c:
        raise HTTPException(404, "company not found")
    for k in ("enabled", "priority", "board_token", "ats", "region"):
        if k in body:
            setattr(c, k, body[k])
    db.commit()
    return {"id": c.id}


@router.delete("/companies/{cid}")
def delete_company(cid: int, db: Session = Depends(get_db)):
    c = db.get(Company, cid)
    if not c:
        raise HTTPException(404, "company not found")
    if db.scalar(select(func.count()).select_from(Job).where(Job.company_id == cid)):
        c.enabled = False  # keep history; just stop scanning
        db.commit()
        return {"disabled": True}
    db.delete(c)
    db.commit()
    return {"deleted": True}


@router.post("/run/scan", status_code=202)
def run_scan_now(bg: BackgroundTasks, s: Settings = Depends(get_settings)):
    bg.add_task(pipeline.run_scan_pipeline, s)
    return {"started": "scan"}


@router.post("/run/wiki-sync", status_code=202)
def run_sync_now(bg: BackgroundTasks, s: Settings = Depends(get_settings)):
    bg.add_task(pipeline.run_wiki_sync, s)
    return {"started": "wiki-sync"}


@router.get("/scans")
def scans(db: Session = Depends(get_db)):
    return [{"id": r.id, "started_at": iso(r.started_at), "status": r.status, "fetched": r.fetched,
             "new": r.new_jobs, "eligible": r.eligible, "notified": r.notified, "sources": r.source_results, "error": r.error}
            for r in db.scalars(select(ScanHistory).order_by(ScanHistory.id.desc()).limit(20))]


@router.get("/health")
def health():
    return {"ok": True}
