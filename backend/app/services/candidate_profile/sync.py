"""Wiki synchronisation: detect new / modified / deleted pages, upsert evidence, snapshot."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateEvidence, ProfileSnapshot, WikiPage, WikiSyncHistory
from app.services.candidate_profile.wiki_parser import (
    Evidence, is_candidate_page, parse_page, sha256_text,
)

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def scan_wiki(root: Path, product_context: set[str]) -> dict[str, str]:
    """Return {relative path: text} for candidate pages. Never follows paths outside root."""
    root = root.resolve()
    pages: dict[str, str] = {}
    for f in sorted(root.rglob("*.md")):
        if not f.is_file() or f.is_symlink():
            continue
        rel = f.relative_to(root).as_posix()
        if is_candidate_page(rel, product_context):
            pages[rel] = f.read_text(encoding="utf-8", errors="replace")
    return pages


def source_url(rel: str, repo_url: str | None) -> str:
    return f"{repo_url.rstrip('/')}/blob/main/V2.0/10-Resume-Wiki/{rel}" if repo_url else ""


def sync_wiki(db: Session, root: Path, product_context: set[str] | None = None,
              repo_url: str | None = "https://github.com/555aaditya/Quant-Journal") -> WikiSyncHistory:
    product_context = product_context or set()
    run = WikiSyncHistory()
    db.add(run)
    db.flush()
    if not root.is_dir():
        run.status, run.error = "failed", f"Wiki path not found: {root}"
        run.finished_at = _now()
        db.commit()
        return run
    try:
        pages = scan_wiki(root, product_context)
        known = {p.path: p for p in db.scalars(select(WikiPage))}
        added, modified, deleted, warnings = [], [], [], []
        changed: dict[str, str] = {}
        for rel, text in pages.items():
            digest = sha256_text(text)
            row = known.get(rel)
            if row is None:
                db.add(WikiPage(path=rel, sha256=digest))
                added.append(rel)
                changed[rel] = text
            elif row.sha256 != digest or row.deleted:
                row.sha256, row.deleted, row.updated_at = digest, False, _now()
                modified.append(rel)
                changed[rel] = text
        for rel, row in known.items():
            if rel not in pages and not row.deleted:
                row.deleted = True
                deleted.append(rel)

        for rel, text in changed.items():
            _replace_page_evidence(db, rel, parse_page(rel, text), source_url(rel, repo_url), warnings)
        for rel in deleted:
            for ev in db.scalars(select(CandidateEvidence).where(CandidateEvidence.source_path == rel)):
                ev.deleted = True

        run.pages_seen, run.added, run.modified, run.deleted = len(pages), added, modified, deleted
        run.warnings, run.status = warnings, "ok"
        run.finished_at = _now()
        db.flush()
        if added or modified or deleted or not db.scalar(select(ProfileSnapshot.id).limit(1)):
            db.add(ProfileSnapshot(sync_id=run.id, content=export_profile(db)))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.exception("wiki sync failed")
        run = db.merge(run)
        run.status, run.error, run.finished_at = "failed", str(exc), _now()
        db.commit()
    return run


def _replace_page_evidence(db: Session, rel: str, items: list[Evidence], url: str, warnings: list) -> None:
    """Upsert by claim key (dedup); anything the page no longer produces is marked deleted."""
    existing = {e.claim_key: e for e in db.scalars(
        select(CandidateEvidence).where(CandidateEvidence.source_path == rel))}
    seen: set[str] = set()
    for it in items:
        key = it.key
        if key in seen:
            continue  # duplicate inside the same page
        seen.add(key)
        row = existing.get(key) or db.scalar(select(CandidateEvidence).where(CandidateEvidence.claim_key == key))
        if row is not None and row.source_path != rel:
            warnings.append(f"duplicate claim '{it.name}' ({it.category}) in {rel}; keeping {row.source_path}")
            continue
        if row is None:
            row = CandidateEvidence(claim_key=key, category=it.category, name=it.name, source_path=rel)
            db.add(row)
        row.description, row.level, row.evidence = it.description, it.level, it.evidence
        row.verification, row.extra, row.source_url = it.verification, it.extra, url
        row.deleted, row.last_synced_at = False, _now()
        if it.extra.get("ambiguous_category"):
            warnings.append(f"{rel}: category could not be determined, stored as 'other' (unverified)")
    for key, row in existing.items():
        if key not in seen:
            row.deleted = True


def export_profile(db: Session) -> dict:
    """Group live evidence by category. This is `candidate_profile`; it never contains product context."""
    out: dict[str, list[dict]] = {}
    for e in db.scalars(select(CandidateEvidence).where(CandidateEvidence.deleted.is_(False))
                        .order_by(CandidateEvidence.category, CandidateEvidence.name)):
        out.setdefault(e.category, []).append({
            "name": e.name, "description": e.description, "level": e.level, "evidence": e.evidence,
            "source_path": e.source_path, "source_url": e.source_url,
            "verification": e.verification, "extra": e.extra,
            "last_synced_at": e.last_synced_at.isoformat() if e.last_synced_at else None,
        })
    return out
