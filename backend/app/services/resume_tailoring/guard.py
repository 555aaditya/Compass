"""Claim guard: flags resume content that contradicts the candidate's own evidence."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app.services.job_matching.candidate_index import CandidateIndex
from app.services.job_matching.vocab import find_terms

MIN_PHRASE = 12


@dataclass
class Violation:
    severity: str   # error | warning
    kind: str       # disputed_phrase | disputed_skill | unsupported_term
    text: str
    reason: str
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _segments(phrase: str) -> list[str]:
    return [p.strip() for p in re.split(r"\.\.\.|…", phrase) if len(p.strip()) >= MIN_PHRASE]


class ClaimGuard:
    def __init__(self, profile: dict[str, list[dict]], overrides: list[dict] | None = None):
        # Claims the candidate has personally decided to stand behind: shown as 'accepted', never blocking.
        self.overrides = [(o["phrase"].lower(), o.get("reason", "")) for o in (overrides or []) if o.get("phrase")]
        self.idx = CandidateIndex.from_profile(profile)
        self.phrases: list[tuple[str, str, str, str]] = []   # (phrase, reason, source, severity)
        self.literals: dict[str, tuple[str, str]] = {}   # lower literal -> (reason, source)
        self.lit_severity: dict[str, str] = {}
        for d in profile.get("disputed_claims", []):
            ex, why = d.get("extra", {}), d.get("description") or d.get("evidence") or "disputed in the wiki"
            # "Unbacked" means only the candidate can confirm it, so it is a warning; "Wrong" contradicts the code.
            sev = "warning" if ex.get("verdict") == "unbacked" else "error"
            for ph in ex.get("phrases", []):
                for seg in _segments(ph):
                    self.phrases.append((seg, why, d["source_path"], sev))
            lits = list(ex.get("literals", []))
            for t in ex.get("terms", []):
                lits += [x.strip() for x in t.split(",")]
            for lit in lits:
                if len(lit) >= 3 and ex.get("kind") != "claim":
                    new_sev = "error" if ex.get("kind") == "skill" or sev == "error" else sev
                    if self.lit_severity.get(lit.lower()) != "error":  # never downgrade an error
                        self.literals[lit.lower()] = (why, d["source_path"])
                        self.lit_severity[lit.lower()] = new_sev
        # a literal the wiki also evidences at 'used' or better is not disputed
        for lit in list(self.literals):
            for t in find_terms(lit):
                if t in self.idx.terms and self.idx.terms[t].status != "familiar" and lit == t.lower():
                    self.literals.pop(lit, None)

    def check(self, text: str) -> list[Violation]:
        out: list[Violation] = []
        low = re.sub(r"\s+", " ", text.lower())
        for phrase, why, src, sev in self.phrases:
            if phrase.lower() in low:
                out.append(Violation(sev, "disputed_phrase", phrase, why, src))
        for lit, (why, src) in self.literals.items():
            if re.search(rf"(?<![\w]){re.escape(lit)}(?![\w])", low):
                out.append(Violation(self.lit_severity.get(lit, "error"), "disputed_skill", lit, why, src))
        for term in sorted(find_terms(text)):
            st = self.idx.status(term)
            if st == "missing":
                out.append(Violation("warning", "unsupported_term", term, "no evidence for this skill in the candidate profile"))
        for v in out:
            low_t = v.text.lower()
            hit = next((r for o, r in self.overrides if o in low_t or low_t in o), None)
            if hit is not None and v.kind != "unsupported_term":
                v.severity, v.reason = "accepted", f"accepted by candidate: {hit or 'no reason given'} (wiki says: {v.reason})"
        seen, uniq = set(), []
        out.sort(key=lambda v: {"error": 0, "warning": 1}.get(v.severity, 2))
        for v in out:
            k = (v.kind, v.text.lower())
            if k not in seen:
                seen.add(k)
                uniq.append(v)
        return uniq


def load_overrides(path) -> list[dict]:
    import json
    from pathlib import Path
    p = Path(path)
    return json.loads(p.read_text()) if p.is_file() else []
