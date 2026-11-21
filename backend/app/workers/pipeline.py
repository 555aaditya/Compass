"""Scheduled workflows: scan -> auto-prepare resumes for qualifying jobs -> notify."""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.database.session import SessionLocal
from app.models import Job, ResumeVersion, ScanHistory, WikiSyncHistory
from app.services.candidate_profile.sync import sync_wiki
from app.services.job_discovery.scan import run_scan
from app.services.job_discovery.store import seed_companies
from app.services.job_matching.settings import load_preferences
from app.services.notifications.channels import build_channels
from app.services.notifications.service import notify_new_matches
from app.services.resume_tailoring.service import prepare_resume

log = logging.getLogger(__name__)


def run_wiki_sync(settings: Settings | None = None) -> int:
    s = settings or get_settings()
    with SessionLocal() as db:
        run = sync_wiki(db, s.wiki_path, set(s.wiki_product_context_pages))
        return run.id


def run_scan_pipeline(settings: Settings | None = None) -> int:
    s = settings or get_settings()
    with SessionLocal() as db:
        seed_companies(db)
        scan = run_scan(db)
        prefs = load_preferences(db)
        if s.auto_generate_resumes:
            qualifying = db.scalars(select(Job).where(
                Job.eligibility == "eligible", Job.active.is_(True), Job.score >= prefs.min_match_score)).all()
            for job in qualifying:
                if db.scalar(select(ResumeVersion.id).where(ResumeVersion.job_id == job.id).limit(1)):
                    continue
                try:
                    prepare_resume(db, job, s)
                except Exception as exc:  # noqa: BLE001  one bad job must not stop the rest
                    log.warning("resume prepare failed for job %s: %s", job.id, exc)
                    db.rollback()
        scan.notified = notify_new_matches(db, build_channels(s), prefs)
        db.commit()
        return scan.id


def recover_interrupted() -> int:
    """Task recovery: runs left in 'running' by a crash are marked interrupted on startup."""
    n = 0
    with SessionLocal() as db:
        for model in (ScanHistory, WikiSyncHistory):
            for row in db.scalars(select(model).where(model.status == "running")):
                row.status, row.error, n = "interrupted", "process stopped before completion", n + 1
        db.commit()
    return n
