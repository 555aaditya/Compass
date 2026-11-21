from app.services.ats_analysis import report as rpt, validator
from app.services.job_matching.requirements import Requirement
from app.services.job_matching.candidate_index import CandidateIndex
from app.services.resume_tailoring.keyword_matrix import build_matrix
from tests.pdfgen import make_pdf

TEX = r"""\documentclass{article}\begin{document}
\begin{center}\textbf{Jane Doe} \\ +91 98765 43210 $|$ \href{mailto:jane@x.com}{jane@x.com} $|$
\href{https://github.com/jane}{github} $|$ \href{https://www.linkedin.com/in/jane}{linkedin}\end{center}
\section{Education}
\resumeSubheading{Some University}{8 CGPA}{Bachelor of Engineering in Computer Science}{2022 -- 2026}
\section{Skills}
\begin{itemize}\small{\item{
\textbf{Languages:} Python, SQL \\
\textbf{Backend:} FastAPI, PostgreSQL \\
}}\end{itemize}
\section{Experience}
\resumeSubheading{Acme}{August 2025 -- Present}{Intern}{Pune}
\resumeItem{Built a payments API with FastAPI and PostgreSQL for internal teams.}
\resumeItem{Wrote Terraform to provision AWS ECS services and CI pipelines.}
\section{Projects}
\resumeProjectHeading{\textbf{Backtester} $|$ \emph{Python}}{2026}
\resumeItem{Implemented an event-driven backtesting engine in pure Python.}
\end{document}"""

GOOD_LINES = ["Jane Doe", "+91 98765 43210 | jane@x.com | github | linkedin", "Education",
              "Some University 8 CGPA", "Bachelor of Engineering in Computer Science 2022 - 2026",
              "Skills", "Languages: Python, SQL", "Backend: FastAPI, PostgreSQL", "Experience",
              "Acme August 2025 - Present Intern Pune",
              "Built a payments API with FastAPI and PostgreSQL for internal teams.",
              "Wrote Terraform to provision AWS ECS services and CI pipelines.", "Projects",
              "Backtester | Python 2026",
              "Implemented an event-driven backtesting engine in pure Python.",
              "A long filler line to get past the minimum text threshold used by the extraction check: " + "word " * 30]
LINKS = ["https://github.com/jane", "https://www.linkedin.com/in/jane", "mailto:jane@x.com"]


def status(rep, name):
    return next(c["status"] for c in rep["checks"] if c["name"] == name)


def test_healthy_pdf_passes_core_checks(tmp_path):
    pdf = make_pdf(tmp_path / "r.pdf", GOOD_LINES, LINKS)
    rep = validator.validate(TEX, pdf)
    for name in ("pdf_text_extraction", "section_headings", "contact_information", "skills_readable",
                 "dates_extractable", "education_extractable", "missing_characters", "bullet_ordering",
                 "hyperlinks", "layout_risks", "content_matches_source"):
        assert status(rep, name) == "pass", (name, rep["checks"])
    assert rep["overall"] == "passed" and rep["pages"] == 1


def test_missing_bullets_and_corrupted_text_detected(tmp_path):
    lines = [l for l in GOOD_LINES if "Terraform" not in l and "backtesting" not in l]
    lines.append("garbled � text")
    pdf = make_pdf(tmp_path / "r.pdf", [l.replace("�", "?") for l in lines], LINKS)
    rep = validator.validate(TEX, pdf)
    assert status(rep, "content_matches_source") in ("fail", "warn")
    assert "Terraform" in str([c for c in rep["checks"] if c["name"] == "content_matches_source"])


def test_reordered_bullets_detected(tmp_path):
    lines = list(GOOD_LINES)
    i, j = lines.index(GOOD_LINES[10]), lines.index(GOOD_LINES[14])
    lines[i], lines[j] = lines[j], lines[i]
    rep = validator.validate(TEX, make_pdf(tmp_path / "r.pdf", lines, LINKS))
    assert status(rep, "bullet_ordering") == "warn"


def test_missing_contact_and_links_flagged(tmp_path):
    lines = [l for l in GOOD_LINES if "@" not in l]
    rep = validator.validate(TEX, make_pdf(tmp_path / "r.pdf", lines, links=[]))
    assert status(rep, "contact_information") == "fail"
    assert status(rep, "hyperlinks") == "warn"


def test_layout_risks_and_page_count(tmp_path):
    risky = TEX.replace("\\begin{document}", "\\usepackage{multicol}\\begin{document}")
    rep = validator.validate(risky, make_pdf(tmp_path / "r.pdf", GOOD_LINES * 3, LINKS, pages=3))
    assert status(rep, "layout_risks") == "warn" and status(rep, "page_count") == "warn"


def test_nonstandard_heading_warns(tmp_path):
    t = TEX.replace("\\section{Projects}", "\\section{Things I Made}")
    lines = [("Things I Made" if l == "Projects" else l) for l in GOOD_LINES]
    rep = validator.validate(t, make_pdf(tmp_path / "r.pdf", lines, LINKS))
    assert status(rep, "section_headings") == "warn"


def test_keyword_coverage_and_report(tmp_path):
    profile = {"programming_languages": [{"name": "Python", "level": "deep", "source_path": "skills.md", "verification": "verified"}],
               "frameworks": [{"name": "FastAPI", "level": "deep", "source_path": "skills.md", "verification": "verified"}]}
    idx = CandidateIndex.from_profile(profile)
    reqs = [Requirement("Python", "language", "required"), Requirement("FastAPI", "framework", "required"),
            Requirement("Kubernetes", "devtool", "required"), Requirement("Terraform", "devtool", "preferred")]
    matrix = build_matrix(reqs, idx)
    assert {m["requirement"]: m["resume_action"] for m in matrix}["Kubernetes"] == "do_not_claim"
    val = validator.validate(TEX, make_pdf(tmp_path / "r.pdf", GOOD_LINES, LINKS))
    rep = rpt.build_report(job={"title": "SWE", "company": "Acme"}, matrix=matrix, validation=val, violations=[],
                           section_order=["Education"], compile_info={"ok": True})
    cov = rep["keyword_coverage"]
    assert cov["required"]["total"] == 3 and cov["required"]["matched_in_resume"] == 2
    assert cov["unsupported_requirements"] == ["Kubernetes"]
    assert "Terraform" in cov["claimed_without_evidence"]  # in the resume text but not backed by the profile
    md = rpt.to_markdown(rep)
    assert "not an ATS score" in md and "Kubernetes" in md
