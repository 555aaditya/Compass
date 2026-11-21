"""ORM entities. Portable between SQLite and PostgreSQL (no dialect-specific types)."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


JOB_STATUSES = [
    "discovered", "shortlisted", "resume_generated", "awaiting_approval", "applied",
    "assessment", "interview", "rejected", "offer", "not_interested", "expired",
]


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    slug: Mapped[str] = mapped_column(String(100), index=True)
    ats: Mapped[str] = mapped_column(String(30))  # greenhouse | lever | ashby
    board_token: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(20), default="global")  # global | india
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1 = highest
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(300))
    title_norm: Mapped[str] = mapped_column(String(300), index=True)
    location: Mapped[str] = mapped_column(String(300), default="")
    work_mode: Mapped[str] = mapped_column(String(20), default="unknown")  # onsite|hybrid|remote|unknown
    description: Mapped[str] = mapped_column(Text, default="")
    apply_url: Mapped[str] = mapped_column(String(1000))
    external_id: Mapped[str] = mapped_column(String(200), default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # deterministic eligibility
    eligibility: Mapped[str] = mapped_column(String(20), default="pending")  # eligible|uncertain|rejected
    eligibility_reasons: Mapped[list] = mapped_column(JSON, default=list)
    experience_min: Mapped[float | None] = mapped_column(Float)
    experience_max: Mapped[float | None] = mapped_column(Float)

    # matching
    score: Mapped[float | None] = mapped_column(Float)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    category: Mapped[str | None] = mapped_column(String(20))

    status: Mapped[str] = mapped_column(String(30), default="discovered", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company] = relationship()
    sources: Mapped[list["JobSource"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    skills: Mapped[list["JobSkill"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobSource(Base):
    """Where a canonical job was seen. One job can have many sources."""
    __tablename__ = "job_sources"
    __table_args__ = (UniqueConstraint("job_id", "source", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(40))
    external_id: Mapped[str] = mapped_column(String(200), default="")
    url: Mapped[str] = mapped_column(String(1000))
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    job: Mapped[Job] = relationship(back_populates="sources")


class JobSkill(Base):
    __tablename__ = "job_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(12))  # required | preferred | mentioned
    job: Mapped[Job] = relationship(back_populates="skills")


class CandidateEvidence(Base):
    """One claim about the candidate with its source. Never mixed with product context."""
    __tablename__ = "candidate_evidence"
    __table_args__ = (UniqueConstraint("claim_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_key: Mapped[str] = mapped_column(String(64))  # hash of category + normalised name
    category: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(20), default="")  # deep | used | touched | ""
    evidence: Mapped[str] = mapped_column(Text, default="")
    source_path: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    verification: Mapped[str] = mapped_column(String(20), default="verified")  # verified|unverified|disputed
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WikiSyncHistory(Base):
    __tablename__ = "wiki_sync_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    pages_seen: Mapped[int] = mapped_column(Integer, default=0)
    added: Mapped[list] = mapped_column(JSON, default=list)
    modified: Mapped[list] = mapped_column(JSON, default=list)
    deleted: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text)


class WikiPage(Base):
    """Content hash per wiki page, used to detect new / modified / deleted pages."""
    __tablename__ = "wiki_pages"
    path: Mapped[str] = mapped_column(String(500), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sync_id: Mapped[int | None] = mapped_column(ForeignKey("wiki_sync_history.id"))
    content: Mapped[dict] = mapped_column(JSON)


class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    directory: Mapped[str] = mapped_column(String(600))
    state: Mapped[str] = mapped_column(String(20), default="prepared")  # prepared|compiled|failed|approved
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    compile_log: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    job: Mapped[Job] = relationship()
    ats_reports: Mapped[list["ATSReport"]] = relationship(back_populates="resume", cascade="all, delete-orphan")


class ATSReport(Base):
    __tablename__ = "ats_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"))
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resume: Mapped[ResumeVersion] = relationship(back_populates="ats_reports")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("job_id", "channel"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))  # sent | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Application(Base):
    """History of manual status changes. The app never submits applications itself."""
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resume_versions.id"))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserSetting(Base):
    __tablename__ = "user_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class ScanHistory(Base):
    __tablename__ = "scan_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    new_jobs: Mapped[int] = mapped_column(Integer, default=0)
    eligible: Mapped[int] = mapped_column(Integer, default=0)
    notified: Mapped[int] = mapped_column(Integer, default=0)
    source_results: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
