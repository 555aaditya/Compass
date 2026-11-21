"""Manual application tracking. The system never submits applications; statuses are set by the user."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import JOB_STATUSES, Application, Job


class InvalidStatus(ValueError):
    pass


def set_status(db: Session, job: Job, status: str, note: str = "", resume_id: int | None = None) -> Job:
    if status not in JOB_STATUSES:
        raise InvalidStatus(f"Unknown status '{status}'. Valid: {', '.join(JOB_STATUSES)}")
    job.status = status
    if status == "applied" and job.applied_at is None:
        job.applied_at = datetime.now(timezone.utc)
    if note:
        job.notes = (job.notes + "\n" if job.notes else "") + note
    db.add(Application(job_id=job.id, status=status, note=note, resume_id=resume_id))
    db.commit()
    return job
