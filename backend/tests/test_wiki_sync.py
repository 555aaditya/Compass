from sqlalchemy import select

from app.models import CandidateEvidence, ProfileSnapshot
from app.services.candidate_profile.sync import export_profile, sync_wiki
from app.services.candidate_profile.wiki_parser import parse_page

PRODUCT = {"projects/compass.md"}


def test_parser_skills_levels_and_disputed():
    from tests.conftest import SKILLS_MD
    items = parse_page("skills.md", SKILLS_MD)
    by = {(i.category, i.name): i for i in items}
    assert by[("programming_languages", "Python 3.12")].level == "deep"
    assert by[("programming_languages", "Go")].level == "touched"
    assert by[("disputed_claims", "Redis")].verification == "disputed"
    assert ("computer_science_fundamentals", "Data structures & algorithms") in by


def test_product_context_and_private_pages_are_excluded(db, wiki):
    run = sync_wiki(db, wiki, PRODUCT, repo_url=None)
    assert run.status == "ok"
    paths = {e.source_path for e in db.scalars(select(CandidateEvidence))}
    assert "projects/compass.md" not in paths
    assert not any(p.startswith("claude-memory") or p == "README.md" for p in paths)
    assert "Celery" not in str(export_profile(db))  # Compass tech never becomes candidate evidence


def test_first_sync_records_pages_and_snapshot(db, wiki):
    run = sync_wiki(db, wiki, PRODUCT, repo_url="https://github.com/x/y")
    assert sorted(run.added) == ["profile.md", "projects/backtester.md", "skills.md"]
    prof = export_profile(db)
    proj = prof["projects"][0]
    assert proj["name"] == "Stock Backtester" and proj["extra"]["strength"] == "A"
    assert proj["source_url"].endswith("projects/backtester.md")
    assert db.scalars(select(ProfileSnapshot)).all()


def test_repeat_sync_is_idempotent(db, wiki):
    sync_wiki(db, wiki, PRODUCT)
    n = len(db.scalars(select(CandidateEvidence)).all())
    run = sync_wiki(db, wiki, PRODUCT)
    assert (run.added, run.modified, run.deleted) == ([], [], [])
    assert len(db.scalars(select(CandidateEvidence)).all()) == n
    assert len(db.scalars(select(ProfileSnapshot)).all()) == 1  # no change, no new snapshot


def test_modified_and_deleted_pages(db, wiki):
    sync_wiki(db, wiki, PRODUCT)
    (wiki / "skills.md").write_text((wiki / "skills.md").read_text().replace("| Go | ● |", "| Go | ●●● |"))
    run = sync_wiki(db, wiki, PRODUCT)
    assert run.modified == ["skills.md"]
    go = db.scalar(select(CandidateEvidence).where(CandidateEvidence.name == "Go"))
    assert go.level == "deep"
    (wiki / "projects" / "backtester.md").unlink()
    run = sync_wiki(db, wiki, PRODUCT)
    assert run.deleted == ["projects/backtester.md"]
    assert not export_profile(db).get("projects")
    assert len(db.scalars(select(ProfileSnapshot)).all()) == 3


def test_new_category_page_is_picked_up_dynamically(db, wiki):
    sync_wiki(db, wiki, PRODUCT)
    (wiki / "publications.md").write_text("---\ntitle: My Paper\n---\n# My Paper\n> A study of X.\n")
    (wiki / "misc.md").write_text("# Something\n> unclear page\n")
    run = sync_wiki(db, wiki, PRODUCT)
    prof = export_profile(db)
    assert prof["research_and_publications"][0]["name"] == "My Paper"
    assert prof["other"][0]["verification"] == "unverified"  # ambiguous category is flagged, not guessed
    assert any("misc.md" in w for w in run.warnings)


def test_missing_wiki_path_reports_failure(db, tmp_path):
    run = sync_wiki(db, tmp_path / "nope")
    assert run.status == "failed" and "not found" in run.error
