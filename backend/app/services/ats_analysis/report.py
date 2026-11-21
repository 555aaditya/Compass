"""ATS keyword coverage + compatibility report (JSON and Markdown)."""
from __future__ import annotations

import re

from app.services.job_matching.vocab import TERMS

DISCLAIMER = ("Keyword coverage is an internal diagnostic. It is not an ATS score and does not predict whether "
              "any employer's ATS will select this resume.")


def keyword_coverage(matrix: list[dict], resume_text: str) -> dict:
    rows = []
    for m in matrix:
        rx = TERMS[m["requirement"]][1] if m["requirement"] in TERMS else re.compile(re.escape(m["requirement"]), re.I)
        in_resume = bool(rx.search(resume_text))
        supported = m["status"] in ("demonstrated", "practically_used", "familiar")
        state = ("matched" if in_resume and supported else "partial" if supported and not in_resume
                 else "unsupported_in_resume" if in_resume else "gap")
        rows.append({**m, "in_resume": in_resume, "supported": supported, "state": state})

    def stat(priority: str) -> dict:
        grp = [r for r in rows if r["priority"] == priority]
        sup = [r for r in grp if r["supported"]]
        mat = [r for r in grp if r["state"] == "matched"]
        return {"total": len(grp), "supported": len(sup), "matched_in_resume": len(mat),
                "coverage_pct": round(100 * len(mat) / len(grp)) if grp else None}

    return {"rows": rows, "required": stat("required"), "preferred": stat("preferred"),
            "unsupported_requirements": [r["requirement"] for r in rows if not r["supported"] and r["priority"] == "required"],
            "claimed_without_evidence": [r["requirement"] for r in rows if r["state"] == "unsupported_in_resume"]}


def build_report(*, job: dict, matrix: list[dict], validation: dict, violations: list[dict],
                 section_order: list[str], compile_info: dict) -> dict:
    cov = keyword_coverage(matrix, validation["extracted_text"])
    recs = []
    if cov["unsupported_requirements"]:
        recs.append("Gaps (not claimable): " + ", ".join(cov["unsupported_requirements"]) + ". Do not add them to the resume.")
    partial = [r["requirement"] for r in cov["rows"] if r["state"] == "partial" and r["priority"] != "mentioned"]
    if partial:
        recs.append("Supported by your evidence but absent from the resume text: " + ", ".join(partial)
                    + ". Add only where it fits a real bullet naturally.")
    for c in validation["checks"]:
        if c["status"] != "pass":
            recs.append(f"{c['name']}: {c['detail']}")
    errs = [v for v in violations if v["severity"] == "error"]
    if errs:
        recs.append(f"{len(errs)} claim(s) contradict your wiki evidence and must be fixed before approval.")
    return {
        "job": job, "disclaimer": DISCLAIMER, "compile": compile_info, "keyword_coverage": cov,
        "validation": {k: v for k, v in validation.items() if k != "extracted_text"},
        "claim_violations": violations, "section_order": section_order, "recommendations": recs,
    }


def to_markdown(r: dict) -> str:
    cov, v = r["keyword_coverage"], r["validation"]
    L = [f"# ATS report: {r['job'].get('title')} at {r['job'].get('company')}", "", f"> {r['disclaimer']}", "",
         "## Summary", "", "| Category | Result |", "|---|---|",
         f"| Required keywords | {cov['required']['matched_in_resume']} of {cov['required']['total']} in resume "
         f"({cov['required']['supported']} supported by evidence) |",
         f"| Preferred keywords | {cov['preferred']['matched_in_resume']} of {cov['preferred']['total']} in resume "
         f"({cov['preferred']['supported']} supported by evidence) |",
         f"| Unsupported requirements | {len(cov['unsupported_requirements'])} |",
         f"| Claim check | {sum(1 for x in r['claim_violations'] if x['severity']=='error')} errors, "
         f"{sum(1 for x in r['claim_violations'] if x['severity']=='warning')} warnings |",
         f"| PDF text extraction ({v['extraction_tool']}) | {next(c['status'] for c in v['checks'] if c['name']=='pdf_text_extraction')} |",
         f"| Overall compatibility checks | {v['overall']} ({v['counts']['pass']} pass, {v['counts']['warn']} warn, {v['counts']['fail']} fail) |",
         "", "## Compatibility checks", "", "| Check | Status | Detail |", "|---|---|---|"]
    L += [f"| {c['name']} | {c['status']} | {c['detail']} |" for c in v["checks"]]
    L += ["", "## Keyword matrix", "", "| Requirement | Kind | Evidence status | In resume | Action |", "|---|---|---|---|---|"]
    L += [f"| {x['requirement']} | {x['kind']} | {x['status']} | {'yes' if x['in_resume'] else 'no'} | {x['resume_action']} |"
          for x in cov["rows"]]
    if r["claim_violations"]:
        L += ["", "## Unsupported or uncertain claims", ""]
        L += [f"- **{x['severity']}** ({x['kind']}): `{x['text']}`: {x['reason']}" for x in r["claim_violations"]]
    L += ["", "## Recommendations", ""] + [f"- {x}" for x in r["recommendations"]]
    return "\n".join(L) + "\n"
