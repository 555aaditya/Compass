"""Job-specific keyword matrix: requirement -> candidate evidence -> resume action."""
from __future__ import annotations

from app.services.job_matching.candidate_index import CandidateIndex
from app.services.job_matching.requirements import Requirement

ACTIONS = {
    "demonstrated": "emphasize",
    "practically_used": "include",
    "familiar": "include_only_if_natural",
    "missing": "do_not_claim",
    "do_not_claim": "do_not_claim",
}
LABEL = {"required": "Required skill", "preferred": "Preferred skill", "mentioned": "Mentioned in description"}


def build_matrix(reqs: list[Requirement], idx: CandidateIndex) -> list[dict]:
    rows = []
    for r in reqs:
        st = idx.status(r.term)
        ev = idx.terms[r.term].sources[:4] if r.term in idx.terms else []
        rows.append({
            "requirement": r.term, "category": r.category, "kind": LABEL[r.priority], "priority": r.priority,
            "priority_rank": {"required": "High", "preferred": "Medium", "mentioned": "Low"}[r.priority],
            "status": st if st != "missing" else "missing", "evidence": ev,
            "resume_action": ACTIONS[st],
            "note": "On the wiki's do-not-claim list" if st == "do_not_claim" else "",
        })
    order = {"required": 0, "preferred": 1, "mentioned": 2}
    rows.sort(key=lambda x: (order[x["priority"]], x["requirement"]))
    return rows
