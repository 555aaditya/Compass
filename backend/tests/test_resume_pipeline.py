import json
import shutil
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.models import ATSReport, Company, Job, JobSkill, ResumeVersion
from app.services.candidate_profile.sync import export_profile, sync_wiki
from app.services.resume_tailoring import latex, service, workspace
from app.services.resume_tailoring.baseline import baseline_resume
from app.services.resume_tailoring.compile import CompileResult, compile_tex, detect_compiler, parse_errors
from app.services.resume_tailoring.guard import ClaimGuard
from tests.pdfgen import make_pdf
from tests.test_ats import GOOD_LINES, LINKS, TEX

DISPUTED = [
    {"name": "Redis", "description": "no evidence", "evidence": "", "source_path": "skills.md", "verification": "disputed",
     "extra": {"kind": "skill", "literals": ["Redis"]}},
    {"name": "x", "description": "goals backend removed", "evidence": "", "source_path": "resume-audit.md",
     "verification": "disputed", "extra": {"kind": "audit", "verdict": "wrong", "phrases": ["quarterly goal tracking"]}},
    {"name": "y", "description": "only you can confirm", "evidence": "", "source_path": "resume-audit.md",
     "verification": "disputed", "extra": {"kind": "audit", "verdict": "unbacked", "phrases": ["2,000 annual hours saved"]}},
]
PROFILE = {"programming_languages": [{"name": "Python", "level": "deep", "source_path": "skills.md", "verification": "verified"}],
           "frameworks": [{"name": "FastAPI", "level": "deep", "source_path": "skills.md", "verification": "verified"}],
           "disputed_claims": DISPUTED}


def test_latex_helpers():
    assert [s.name for s in latex.sections(TEX)] == ["Education", "Skills", "Experience", "Projects"]
    assert len(latex.bullets(TEX)) == 3
    assert latex.skill_lines(latex.sections(TEX)[1].body)[0] == ("Languages", ["Python", "SQL"])
    assert "Languages: Python, SQL" in latex.tex_to_text(TEX)
    assert latex.tex_to_text(r"\resumeItem{Cut costs by 50\% with \textbf{Redis} \& Go}").strip() == "Cut costs by 50% with Redis & Go"


def test_guard_flags_wrong_as_error_unbacked_as_warning_and_unsupported_terms():
    g = ClaimGuard(PROFILE)
    v = {(x.kind, x.text.lower()): x.severity for x in g.check(
        "Built quarterly goal tracking with Redis and Kubernetes; 2,000 annual hours saved")}
    assert v[("disputed_phrase", "quarterly goal tracking")] == "error"
    assert v[("disputed_phrase", "2,000 annual hours saved")] == "warning"
    assert v[("disputed_skill", "redis")] == "error"
    assert v[("unsupported_term", "kubernetes")] == "warning"
    assert not any(k[1] in ("python", "fastapi") for k in v)  # evidenced skills are never flagged


def test_baseline_removes_disputed_skills_and_reorders_projects_without_inventing():
    tex = TEX.replace(r"\textbf{Backend:} FastAPI, PostgreSQL \\", r"\textbf{Backend:} Redis, PostgreSQL, FastAPI \\") \
             .replace(r"\section{Projects}" + "\n" + r"\resumeProjectHeading{\textbf{Backtester} $|$ \emph{Python}}{2026}",
                      r"\section{Projects}" + "\n" + r"\resumeProjectHeading{\textbf{Chat} $|$ \emph{Node.js, React}}{2025}"
                      + "\n" + r"\resumeItem{Built a chat app.}" + "\n" + r"\resumeProjectHeading{\textbf{Backtester} $|$ \emph{Python}}{2026}")
    new, notes = baseline_resume(tex, {"Python", "FastAPI"}, ClaimGuard(PROFILE))
    assert "Redis" not in new and any("Redis" in n for n in notes)
    assert latex.skill_lines(latex.sections(new)[1].body)[1][1][0] == "FastAPI"   # JD match moved first
    assert new.index("Backtester") < new.index("Chat")                           # more relevant project first
    assert set(latex.bullets(new)) == set(latex.bullets(tex))                    # no bullet added or altered


def test_compile_without_compiler_reports_clearly(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda c: None)
    assert detect_compiler() is None
    r = compile_tex(tmp_path)
    assert not r.ok and "No LaTeX compiler" in r.log


def test_compile_error_parsing():
    log = "! Undefined control sequence.\nl.42 \\foo\n\n./resume.tex:7: ! Missing } inserted.\n"
    errs = parse_errors(log)
    assert errs[0]["line"] == 42 and errs[1]["line"] == 7


def test_compile_uses_argument_list_without_shell(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr("shutil.which", lambda c: "/usr/bin/" + c)
    def fake_run(cmd, **kw):
        calls["cmd"], calls["kw"] = cmd, kw
        (tmp_path / "resume.pdf").write_bytes(b"%PDF")
        class P: returncode, stdout, stderr = 0, "ok", ""
        return P()
    monkeypatch.setattr("subprocess.run", fake_run)
    assert compile_tex(tmp_path).ok
    assert isinstance(calls["cmd"], list) and "-no-shell-escape" in calls["cmd"] and not calls["kw"].get("shell")


# ---- service level ----

@pytest.fixture
def env(db, wiki, tmp_path):
    master_dir = tmp_path / "master"
    master_dir.mkdir()
    (master_dir / "main.tex").write_text(TEX)
    s = Settings(_env_file=None, master_resume_path=master_dir / "main.tex",
                 generated_resumes_path=tmp_path / "generated", wiki_path=wiki)
    sync_wiki(db, wiki, {"projects/compass.md"})
    c = Company(name="Acme Corp", slug="acme-corp", ats="greenhouse", board_token="a")
    db.add(c); db.flush()
    job = Job(dedup_key="k", company_id=c.id, title="Backend Engineer", title_norm="backend engineer", location="Pune",
              apply_url="https://acme/1", description="Python and FastAPI", eligibility="eligible", score=80,
              category="strong", analysis={"relevant_projects": [{"name": "Stock Backtester", "path": "projects/backtester.md"}],
                                           "recommended_emphasis": "APIs"})
    job.skills = [JobSkill(term="Python", category="language", priority="required"),
                  JobSkill(term="FastAPI", category="framework", priority="required"),
                  JobSkill(term="Kubernetes", category="devtool", priority="preferred")]
    db.add(job); db.commit()
    return s, job, master_dir / "main.tex"


def test_prepare_creates_workspace_and_never_touches_master(db, env):
    s, job, master = env
    before = master.read_bytes()
    rv = service.prepare_resume(db, job, s)
    d = Path(rv.directory)
    assert d == (s.generated_resumes_path / "acme-corp" / str(job.id)).resolve()
    for f in ("resume.tex", "job_context.json", "match_analysis.json", "keyword_matrix.json", "evidence_pack.md", "TAILOR.md"):
        assert (d / f).is_file(), f
    assert master.read_bytes() == before
    matrix = {m["requirement"]: m["resume_action"] for m in json.loads((d / "keyword_matrix.json").read_text())}
    assert matrix["Kubernetes"] == "do_not_claim" and matrix["Python"] == "emphasize"
    assert "Stock Backtester" in (d / "evidence_pack.md").read_text() or "Source:" in (d / "evidence_pack.md").read_text()
    assert "compass" not in (d / "evidence_pack.md").read_text().lower().replace("compass-job", "")
    assert job.status == "resume_generated" and rv.version == 1


def test_regeneration_keeps_previous_version(db, env):
    s, job, _ = env
    service.prepare_resume(db, job, s)
    rv2 = service.prepare_resume(db, job, s)
    assert rv2.version == 2 and (s.generated_resumes_path / "acme-corp" / f"{job.id}.v1").is_dir()


def test_master_tamper_is_detected(db, env):
    s, job, master = env
    (master.parent / "manifest.json").write_text(json.dumps({"files": {"main.tex": "0" * 64}}))
    with pytest.raises(RuntimeError, match="Master resume changed"):
        service.prepare_resume(db, job, s)


def test_missing_master_has_actionable_error(db, env):
    s, job, master = env
    master.unlink()
    with pytest.raises(FileNotFoundError, match="import_master"):
        service.prepare_resume(db, job, s)


def test_path_traversal_is_rejected(tmp_path):
    c = Company(name="../../etc", slug="x", ats="g", board_token="t")
    j = Job(id=1, company=c, title="t", title_norm="t", apply_url="u", dedup_key="k")
    d = workspace.job_dir(tmp_path, j)
    assert tmp_path.resolve() in d.parents and ".." not in d.parts


def test_finalize_without_compiler_marks_failed_but_writes_reports(db, env, monkeypatch):
    s, job, _ = env
    monkeypatch.setattr("shutil.which", lambda c: None)
    rv = service.prepare_resume(db, job, s)
    out = service.finalize_resume(db, rv, s)
    assert out["state"] == "failed" and "No LaTeX compiler" in out["compile"]["log_tail"] + rv.compile_log
    assert (Path(rv.directory) / "changes.md").is_file() and (Path(rv.directory) / "ats_report.md").is_file()
    with pytest.raises(service.ApprovalBlocked):
        service.approve_resume(db, rv)


def test_finalize_success_then_approval_gate(db, env, monkeypatch):
    s, job, _ = env
    rv = service.prepare_resume(db, job, s)
    d = Path(rv.directory)
    def fake_compile(directory, main, compiler):
        pdf = make_pdf(directory / "resume.pdf", GOOD_LINES, LINKS)
        return CompileResult(True, "latexmk", "ok", pdf)
    monkeypatch.setattr(service, "compile_tex", fake_compile)
    out = service.finalize_resume(db, rv, s)
    assert out["state"] == "compiled" and (d / "ats_report.json").is_file() and (d / "extracted_resume.txt").is_file()
    rep = json.loads((d / "ats_report.json").read_text())
    assert rep["keyword_coverage"]["unsupported_requirements"] == [] and "not an ATS score" in rep["disclaimer"]
    assert db.scalar(select(ATSReport)) is not None and job.status == "awaiting_approval"
    # no error-level claims in this resume, so approval succeeds
    assert service.approve_resume(db, rv).approved

    # an unsupported claim blocks approval unless forced
    rv2 = service.prepare_resume(db, job, s)
    (Path(rv2.directory) / "resume.tex").write_text(TEX.replace("Built a payments API", "Built a payments API with Redis caching,"))
    service.finalize_resume(db, rv2, s)
    from app.services.resume_tailoring.service import ApprovalBlocked
    with pytest.raises(ApprovalBlocked, match="contradict"):
        service.approve_resume(db, rv2)
    assert service.approve_resume(db, rv2, force=True).approved
