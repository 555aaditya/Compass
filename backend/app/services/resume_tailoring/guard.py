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
    def __init__(self, profile: dict[str, list[dict]]):
        self.idx = CandidateIndex.from_profile(profile)
        self.phrases: list[tuple[str, str, str]] = []   # (phrase, reason, source)
        self.literals: dict[str, tuple[str, str]] = {}   # lower literal -> (reason, source)
        for d in profile.get("disputed_claims", []):
            ex, why = d.get("extra", {}), d.get("description") or d.get("evidence") or "disputed in the wiki"
            for ph in ex.get("phrases", []):
                for seg in _segments(ph):
                    self.phrases.append((seg, why, d["source_path"]))
            lits = list(ex.get("literals", []))
            for t in ex.get("terms", []):
                lits += [x.strip() for x in t.split(",")]
            for lit in lits:
                if len(lit) >= 3 and ex.get("kind") != "claim":
                    self.literals[lit.lower()] = (why, d["source_path"])
        # a literal the wiki also evidences at 'used' or better is not disputed
        for lit in list(self.literals):
            for t in find_terms(lit):
                if t in self.idx.terms and self.idx.terms[t].status != "familiar" and lit == t.lower():
                    self.literals.pop(lit, None)

    def check(self, text: str) -> list[Violation]:
        out: list[Violation] = []
        low = re.sub(r"\s+", " ", text.lower())
        for phrase, why, src in self.phrases:
            if phrase.lower() in low:
                out.append(Violation("error", "disputed_phrase", phrase, why, src))
        for lit, (why, src) in self.literals.items():
            if re.search(rf"(?<![\w]){re.escape(lit)}(?![\w])", low):
                out.append(Violation("error", "disputed_skill", lit, why, src))
        for term in sorted(find_terms(text)):
            st = self.idx.status(term)
            if st == "missing":
                out.append(Violation("warning", "unsupported_term", term, "no evidence for this skill in the candidate profile"))
        seen, uniq = set(), []
        for v in out:
            k = (v.kind, v.text.lower())
            if k not in seen:
                seen.add(k)
                uniq.append(v)
        return uniq
