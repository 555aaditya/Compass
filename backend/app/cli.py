"""Command line entry point: manual runs without the dashboard (also used by Claude Code tailoring sessions)."""
from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.session import SessionLocal
from app.main import migrate
from app.models import Job, ResumeVersion
from app.services.resume_tailoring import service
from app.workers import pipeline


def latest_resume(db, job_id: int) -> ResumeVersion:
    rv = db.scalar(select(ResumeVersion).where(ResumeVersion.job_id == job_id).order_by(ResumeVersion.id.desc()))
    if rv is None:
        sys.exit(f"No resume prepared for job {job_id}. Run: python scripts/resume.py prepare {job_id}")
    return rv


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="compass")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync", help="sync the Quant-Journal wiki into the candidate profile")
    sub.add_parser("scan", help="scan sources, score jobs, prepare resumes, notify")
    sp = sub.add_parser("snapshot", help="write a read-only static jobs page")
    sp.add_argument("--out", default="../site")
    jl = sub.add_parser("jobs", help="list top jobs")
    jl.add_argument("--min-score", type=float, default=0)
    jl.add_argument("--limit", type=int, default=20)
    for name in ("prepare", "finalize", "approve"):
        p = sub.add_parser(name)
        p.add_argument("job_id", type=int)
        if name == "approve":
            p.add_argument("--force", action="store_true", help="approve despite claim errors (you vouch for them)")
        if name == "finalize":
            p.add_argument("--compiler")
    a = ap.parse_args(argv)
    setup_logging()
    migrate()
    s = get_settings()
    if a.cmd == "sync":
        pipeline.run_wiki_sync(s)
        from app.models import WikiSyncHistory
        with SessionLocal() as db:
            r = db.scalar(select(WikiSyncHistory).order_by(WikiSyncHistory.id.desc()))
            print(json.dumps({"status": r.status, "pages": r.pages_seen, "added": r.added, "modified": r.modified,
                              "deleted": r.deleted, "warnings": r.warnings, "error": r.error}, indent=2))
        return 0 if r.status == "ok" else 1
    if a.cmd == "snapshot":
        from pathlib import Path
        from app.snapshot.export import export_snapshot
        with SessionLocal() as db:
            print(f"Wrote {export_snapshot(db, Path(a.out))} jobs to {a.out}")
        return 0
    if a.cmd == "scan":
        pipeline.run_scan_pipeline(s)
        a.cmd, a.min_score, a.limit = "jobs", 0, 20
    with SessionLocal() as db:
        if a.cmd == "jobs":
            for j in db.scalars(select(Job).where(Job.active.is_(True), Job.score >= a.min_score)
                                .order_by(Job.score.desc().nullslast()).limit(a.limit)):
                print(f"{j.id:>5}  {j.score or 0:5.1f}  {j.category or '-':9} {j.eligibility:9} {j.company.name} | {j.title} | {j.location}")
            return 0
        job = db.get(Job, a.job_id)
        if job is None:
            sys.exit(f"job {a.job_id} not found")
        if a.cmd == "prepare":
            rv = service.prepare_resume(db, job, s)
            print(f"Workspace ready: {rv.directory}\nEdit resume.tex following TAILOR.md, then: python scripts/resume.py finalize {job.id}")
        elif a.cmd == "finalize":
            out = service.finalize_resume(db, latest_resume(db, job.id), s, a.compiler)
            print(json.dumps(out, indent=2, default=str))
            return 0 if out["state"] == "compiled" else 1
        elif a.cmd == "approve":
            try:
                rv = service.approve_resume(db, latest_resume(db, job.id), a.force)
            except service.ApprovalBlocked as e:
                sys.exit(f"Blocked: {e}")
            print(f"Approved resume v{rv.version} for job {job.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
