"""Scan orchestration: fetch -> filter -> upsert -> score. Each company is isolated so one failure never aborts a scan."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Job, JobSkill, ScanHistory
from app.services.candidate_profile.sync import export_profile
from app.services.job_discovery.base import SourceError, make_client
from app.services.job_discovery.registry import ADAPTERS
from app.services.job_discovery.store import upsert_job
from app.services.job_matching import eligibility as elig_mod
from app.services.job_matching.candidate_index import CandidateIndex
from app.services.job_matching.preferences import Preferences
from app.services.job_matching.requirements import extract_requirements
from app.services.job_matching.scoring import score_job
from app.services.job_matching.settings import load_preferences

log = logging.getLogger(__name__)


def evaluate_job(db: Session, job: Job, idx: CandidateIndex, prefs: Preferences, remote_flag=None, country="") -> None:
    """Apply eligibility + scoring to a stored job and persist the result."""
    e = elig_mod.evaluate(job.title, job.location, job.description, job.posted_at, prefs,
                          remote_flag=remote_flag, country=country)
    job.eligibility, job.eligibility_reasons = e.status, e.reasons
    job.work_mode, job.experience_min, job.experience_max = e.work_mode, e.experience_min, e.experience_max
    reqs = extract_requirements(job.title, job.description)
    job.skills = [JobSkill(term=r.term, category=r.category, priority=r.priority) for r in reqs]
    if e.status == "rejected":
        job.score, job.category, job.analysis, job.score_breakdown = None, "rejected", {}, {}
        return
    res = score_job(title=job.title, description=job.description, posted_at=job.posted_at, reqs=reqs,
                    elig=e, idx=idx, prefs=prefs)
    job.score, job.category, job.score_breakdown, job.analysis = (
        res["score"], res["category"], res["breakdown"], res["analysis"])


def run_scan(db: Session, client: httpx.Client | None = None, only: list[str] | None = None) -> ScanHistory:
    scan = ScanHistory()
    db.add(scan)
    db.commit()
    own_client = client is None
    client = client or make_client()
    prefs = load_preferences(db)
    idx = CandidateIndex.from_profile(export_profile(db))
    now = datetime.now(timezone.utc)
    results: dict[str, dict] = {}
    try:
        companies = db.scalars(select(Company).where(Company.enabled.is_(True)).order_by(Company.priority)).all()
        for c in companies:
            if only and c.name not in only:
                continue
            adapter = ADAPTERS.get(c.ats)
            if adapter is None:
                continue
            stat = {"fetched": 0, "new": 0, "kept": 0, "rejected": 0, "error": None, "reasons": {}}
            results[c.name] = stat
            try:
                raws = adapter.fetch(c.name, c.board_token, client)
            except SourceError as exc:
                c.consecutive_failures += 1
                c.last_error = str(exc)
                stat["error"] = str(exc)
                log.warning("source %s failed: %s", c.name, exc)
                db.commit()
                continue
            stat["fetched"] = len(raws)
            seen_ids: set[int] = set()
            for raw in raws:
                if not raw.url or not raw.title:
                    continue  # missing required fields: never fabricate
                e = elig_mod.evaluate(raw.title, raw.location, raw.description_text, raw.posted_at, prefs,
                                      remote_flag=raw.remote_flag, country=raw.country)
                if e.status == "rejected":
                    stat["rejected"] += 1
                    key = re.sub(r"\d+\+? years.*|\(.*|:.*", "", e.rejections[0]).strip() if e.rejections else "rejected"
                    stat["reasons"][key] = stat["reasons"].get(key, 0) + 1
                    continue
                job, created = upsert_job(db, c, raw, now)
                seen_ids.add(job.id)
                evaluate_job(db, job, idx, prefs, raw.remote_flag, raw.country)
                stat["kept"] += 1
                stat["new"] += int(created)
            # postings that vanished from a successfully fetched board are expired
            for job in db.scalars(select(Job).where(Job.company_id == c.id, Job.active.is_(True))):
                if job.id not in seen_ids:
                    job.active = False
                    if job.status == "discovered":
                        job.status = "expired"
            c.last_ok_at, c.consecutive_failures, c.last_error = now, 0, None
            db.commit()
        scan.fetched = sum(r["fetched"] for r in results.values())
        scan.new_jobs = sum(r["new"] for r in results.values())
        scan.eligible = sum(r["kept"] for r in results.values())
        scan.status = "ok" if not all(r["error"] for r in results.values()) or not results else "failed"
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.exception("scan crashed")
        scan = db.merge(scan)
        scan.status, scan.error = "failed", str(exc)
    finally:
        if own_client:
            client.close()
    scan.source_results, scan.finished_at = results, datetime.now(timezone.utc)
    db.commit()
    return scan
