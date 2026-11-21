"""ATS compatibility checks on a compiled resume. Diagnostics only: never a pass probability."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader

from app.services.resume_tailoring import latex

STANDARD_HEADINGS = {"education", "skills", "technical skills", "experience", "projects", "summary",
                     "achievements", "publications", "certifications", "competitive programming"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
DATE = re.compile(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(19|20)\d{2}\s*[–—-]\s*"
                  r"((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(19|20)\d{2}|Present)", re.I)
LAYOUT_RISKS = [(r"\\usepackage(?:\[[^\]]*\])?\{multicol\}|\\begin\{multicols\}|twocolumn", "multi-column layout"),
                (r"\\includegraphics", "embedded image"), (r"\\begin\{minipage\}", "minipage (side-by-side layout)"),
                (r"\\fbox|\\framebox|\\tcbox|tikzpicture", "text box / drawing"),
                (r"\\fancyhead|\\fancyfoot|\\rhead|\\lhead|\\cfoot", "header/footer content"),
                (r"\\textcolor\{white\}|\\color\{white\}", "white text (hidden keywords)")]
BAD_CHARS = re.compile(r"\ufffd|\(cid:\d+\)|[\ue000-\uf8ff]")


def extract_text(pdf: Path) -> tuple[str, str]:
    """Return (text, tool). Uses pdftotext when present, otherwise pypdf."""
    if shutil.which("pdftotext"):
        p = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True,
                           timeout=60, check=False)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout, "pdftotext"
    reader = PdfReader(str(pdf))
    return "\n".join((pg.extract_text() or "") for pg in reader.pages), "pypdf"


def pdf_links(pdf: Path) -> list[str]:
    links = []
    for pg in PdfReader(str(pdf)).pages:
        for a in pg.get("/Annots") or []:
            obj = a.get_object()
            act = obj.get("/A")
            if act and act.get_object().get("/URI"):
                links.append(str(act.get_object()["/URI"]))
    return links


def _norm(s: str) -> str:
    s = s.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9+#]+", " ", s.lower()).strip()


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def validate(tex: str, pdf: Path, master_pages: int | None = None) -> dict:
    text, tool = extract_text(pdf)
    pages = len(PdfReader(str(pdf)).pages)
    checks: list[dict] = []
    norm_text, intended = _norm(text), latex.tex_to_text(tex)

    checks.append(_check("pdf_text_extraction", "pass" if len(text.strip()) > 200 else "fail",
                         f"{len(text)} characters extracted with {tool}"))

    # headings
    tex_secs = [s.name for s in latex.sections(tex)]
    missing = [s for s in tex_secs if _norm(s) not in norm_text]
    nonstd = [s for s in tex_secs if s.lower() not in STANDARD_HEADINGS]
    checks.append(_check("section_headings", "fail" if missing else "warn" if nonstd else "pass",
                         f"missing in PDF text: {missing}" if missing else
                         f"non-standard heading names: {nonstd}" if nonstd else f"{len(tex_secs)} standard headings found"))

    # contact
    head = text[:900]
    emails, phones = EMAIL.findall(text), PHONE.findall(head)
    links = pdf_links(pdf)
    gh = any("github.com" in u for u in links) or "github" in norm_text
    li = any("linkedin.com" in u for u in links) or "linkedin" in norm_text
    contact_issues = [x for x, ok in (("email", emails), ("phone", phones), ("github", gh), ("linkedin", li)) if not ok]
    checks.append(_check("contact_information", "fail" if "email" in contact_issues or "phone" in contact_issues
                         else "warn" if contact_issues else "pass",
                         f"not found: {contact_issues}" if contact_issues else "email, phone, GitHub and LinkedIn present"))
    checks.append(_check("contact_in_top_of_page", "pass" if emails and text.find(emails[0]) < 600 else "warn",
                         "email appears near the top" if emails and text.find(emails[0]) < 600 else "email is not near the top"))

    # skills readable
    skills_secs = [s for s in latex.sections(tex) if s.name.lower() in ("skills", "technical skills")]
    items = [i for s in skills_secs for _, its in latex.skill_lines(s.body) for i in its]
    absent = [i for i in items if _norm(i) not in norm_text]
    checks.append(_check("skills_readable", "fail" if items and len(absent) > len(items) * 0.2 else "warn" if absent else "pass",
                         f"{len(items) - len(absent)}/{len(items)} skills found" + (f"; missing: {absent[:8]}" if absent else "")))

    # dates and education
    dates = DATE.findall(text)
    checks.append(_check("dates_extractable", "pass" if len(dates) >= 2 else "warn", f"{len(dates)} date ranges found"))
    edu = "education" in norm_text and bool(re.search(r"b\.?e\.?|b\.?tech|bachelor|university|college", text, re.I))
    checks.append(_check("education_extractable", "pass" if edu else "warn", "education section and degree found" if edu else "degree line not found"))

    # missing / corrupted characters
    bad = BAD_CHARS.findall(text)
    checks.append(_check("missing_characters", "fail" if bad else "pass", f"{len(bad)} replacement/private-use characters" if bad else "none"))

    # bullet order + content coverage
    bl = latex.bullets(tex)
    pos, last, misordered, lost = [], -1, 0, []
    for b in bl:
        key = _norm(b)[:45]
        at = norm_text.find(key) if key else -1
        if at == -1:
            lost.append(b[:50])
            continue
        if at < last:
            misordered += 1
        last = max(last, at)
        pos.append(at)
    checks.append(_check("bullet_ordering", "warn" if misordered else "pass",
                         f"{misordered} bullets appear out of order" if misordered else f"{len(pos)} bullets in order"))
    iw = set(_norm(intended).split())
    cov = len(iw & set(norm_text.split())) / len(iw) if iw else 0
    checks.append(_check("content_matches_source", "fail" if cov < 0.9 or len(lost) > max(1, len(bl) * 0.1) else "warn" if cov < 0.97 else "pass",
                         f"{cov:.0%} of intended words found in PDF text; {len(lost)} bullets not found"
                         + (f": {lost[:3]}" if lost else "")))

    # hyperlinks
    tex_urls = re.findall(r"\\href\{([^}]+)\}", latex.strip_comments(tex))
    web = [u for u in tex_urls if u.startswith("http")]
    missing_links = [u for u in web if u not in links]
    bad_urls = [u for u in links if not re.match(r"^(https?://|mailto:)\S+$", u)]
    checks.append(_check("hyperlinks", "fail" if bad_urls else "warn" if missing_links else "pass",
                         f"{len(links)} link annotations" + (f"; not in PDF: {missing_links[:4]}" if missing_links else "")
                         + (f"; malformed: {bad_urls[:3]}" if bad_urls else "")))

    # layout
    risks = [label for pat, label in LAYOUT_RISKS if re.search(pat, latex.strip_comments(tex))]
    checks.append(_check("layout_risks", "warn" if risks else "pass", ", ".join(risks) if risks else "single-column, text-only"))
    pg_status = "pass" if pages <= 2 and (master_pages is None or abs(pages - master_pages) <= 1) else "warn"
    checks.append(_check("page_count", pg_status, f"{pages} page(s)" + (f" (master: {master_pages})" if master_pages else "")))

    counts = {s: sum(1 for c in checks if c["status"] == s) for s in ("pass", "warn", "fail")}
    return {"extraction_tool": tool, "pages": pages, "checks": checks, "counts": counts,
            "extracted_text": text, "links": links,
            "overall": "failed" if counts["fail"] else "warnings" if counts["warn"] else "passed"}
