"""Persistence of discovered jobs: dedup, source association, history."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Job, JobSource
from app.services.job_discovery.base import RawJob
from app.services.job_discovery.text import normalise_title
from app.services.job_discovery.watchlist import INDIA_MANUAL, MANUAL, VERIFIED


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def seed_companies(db: Session) -> int:
    n = 0
    have = {c.name for c in db.scalars(select(Company))}
    rows = [(*v, True) for v in VERIFIED] + [
        (m, "manual", "", "india" if m in INDIA_MANUAL else "global", 5, False) for m in MANUAL]
    for name, ats, token, region, prio, enabled in rows:
        if name in have:
            continue
        db.add(Company(name=name, slug=slugify(name), ats=ats, board_token=token, region=region,
                       priority=prio, enabled=enabled))
        n += 1
    db.commit()
    return n


def dedup_key(company_slug: str, title: str, location: str) -> str:
    primary_loc = re.split(r"[;|/]", location)[0]
    primary_loc = re.sub(r"[^a-z ]+", "", primary_loc.lower()).strip()
    raw = f"{company_slug}|{normalise_title(title)}|{primary_loc}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def upsert_job(db: Session, company: Company, raw: RawJob, now: datetime | None = None) -> tuple[Job, bool]:
    """Insert or refresh a canonical job. Returns (job, created)."""
    now = now or datetime.now(timezone.utc)
    key = dedup_key(company.slug, raw.title, raw.location)
    job = db.scalar(select(Job).where(Job.dedup_key == key))
    if job is None:
        # same posting under a different title/location spelling: match by source id or URL
        sid = db.scalar(select(JobSource).where(JobSource.source == raw.source,
                                                JobSource.external_id == raw.external_id)) if raw.external_id else None
        job = sid.job if sid else db.scalar(select(Job).where(Job.apply_url == raw.url))
    created = job is None
    if created:
        job = Job(dedup_key=key, company_id=company.id, title=raw.title, title_norm=normalise_title(raw.title),
                  apply_url=raw.url, first_seen_at=now)
        db.add(job)
    job.location, job.description = raw.location, raw.description_text or job.description
    job.external_id = raw.external_id or job.external_id
    job.posted_at = raw.posted_at or job.posted_at
    job.last_seen_at, job.active = now, True
    if job.status == "expired":
        job.status = "discovered"
    db.flush()
    src = db.scalar(select(JobSource).where(JobSource.job_id == job.id, JobSource.source == raw.source,
                                            JobSource.external_id == raw.external_id))
    if src is None:
        db.add(JobSource(job_id=job.id, source=raw.source, external_id=raw.external_id, url=raw.url))
    else:
        src.seen_at, src.url = now, raw.url
    return job, created
