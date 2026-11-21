"""Notification policy: threshold, eligibility, per-channel dedup, daily limit, retries."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Job, Notification, ResumeVersion
from app.services.job_matching.preferences import Preferences
from app.services.notifications.channels import Channel, ChannelError

log = logging.getLogger(__name__)


def format_message(job: Job, resume: ResumeVersion | None, dashboard_url: str = "") -> tuple[str, str]:
    a = job.analysis or {}
    sk = lambda key: ", ".join(m["term"] for m in a.get(key, [])[:8]) or "none"  # noqa: E731
    projects = ", ".join(p["name"].split(" (")[0] for p in a.get("relevant_projects", [])) or "none"
    exp = job.experience_min
    exp_s = "not stated" if exp is None else ("fresher / 0+ years" if exp == 0 else f"{exp:g}+ years")
    resume_s = "not prepared" if resume is None else ("approved" if resume.approved else f"prepared ({resume.state}), awaiting approval")
    subject = f"[{(job.category or '').title()} {job.score:.0f}] {job.title} at {job.company.name}"
    lines = [
        f"Company: {job.company.name}", f"Title: {job.title}", f"Location: {job.location or 'n/a'} ({job.work_mode})",
        f"Experience: {exp_s}", f"Match score: {job.score:.0f}/100",
        f"Why: {'; '.join(a.get('why_matches', [])) or 'n/a'}", f"Matching skills: {sk('matching_skills')}",
        f"Missing skills: {sk('missing_skills')}", f"Relevant projects: {projects}",
        f"Discovered: {job.first_seen_at:%Y-%m-%d}", f"Tailored resume: {resume_s}", f"Apply: {job.apply_url}",
    ]
    if job.eligibility == "uncertain":
        lines.insert(5, "Note: eligibility uncertain: " + "; ".join(job.eligibility_reasons))
    if dashboard_url:
        lines.append(f"Dashboard: {dashboard_url}/jobs/{job.id}")
    return subject, "\n".join(lines)


def notify_new_matches(db: Session, channels: dict[str, Channel], prefs: Preferences, dashboard_url: str = "",
                       retries: int = 3, sleep=time.sleep) -> int:
    """Send each qualifying job once per channel. Returns number of messages sent."""
    sent_total = 0
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(0)
    today = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.status == "sent", Notification.sent_at >= start_of_day)) or 0
    jobs = db.scalars(select(Job).where(
        Job.eligibility == "eligible", Job.active.is_(True), Job.score >= prefs.min_match_score,
        Job.status.in_(["discovered", "shortlisted", "resume_generated", "awaiting_approval"])
    ).order_by(Job.score.desc())).all()
    for job in jobs:
        for name, ch in channels.items():
            if not prefs.notification_channels.get(name) or not ch.configured():
                continue
            if today >= prefs.daily_notification_limit:
                return sent_total
            existing = db.scalar(select(Notification).where(Notification.job_id == job.id, Notification.channel == name))
            if existing and existing.status == "sent":
                continue
            resume = db.scalar(select(ResumeVersion).where(ResumeVersion.job_id == job.id)
                               .order_by(ResumeVersion.id.desc()))
            subject, body = format_message(job, resume, dashboard_url)
            row = existing or Notification(job_id=job.id, channel=name, status="failed")
            db.add(row)
            for attempt in range(1, retries + 1):
                row.attempts = attempt
                try:
                    ch.send(subject, body)
                    row.status, row.error, row.sent_at = "sent", None, datetime.now(timezone.utc)
                    sent_total += 1
                    today += 1
                    break
                except ChannelError as exc:
                    row.status, row.error = "failed", str(exc)
                    if attempt < retries:
                        sleep(2 ** attempt)
            db.commit()
    return sent_total
