"""Small, dependency-free helpers for the Jake-style LaTeX resume: sections, bullets, skills, plain text."""
from __future__ import annotations

import re
from dataclasses import dataclass

_SECTION = re.compile(r"\\section\*?\{([^}]*)\}")
_ESC = {r"\&": "&", r"\%": "%", r"\$": "$", r"\#": "#", r"\_": "_", r"\{": "{", r"\}": "}", "~": " ",
        "---": "—", "--": "–", r"\\": "\n"}


def strip_comments(tex: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", tex)


def _take_group(s: str, i: int) -> tuple[str, int]:
    """s[i] == '{'. Return (inner, index after matching '}')."""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def tex_to_text(tex: str) -> str:
    """Approximate the text a PDF of this LaTeX would contain (used for ATS comparison)."""
    s = strip_comments(tex)
    if "\\begin{document}" in s:
        s = s.split("\\begin{document}", 1)[1].split("\\end{document}")[0]
    s = re.sub(r"\\href\{[^}]*\}", "", s)
    s = re.sub(r"\\(?:vspace|hspace|setlength)\*?\{[^}]*\}", " ", s)
    s = re.sub(r"\\(?:titlerule|newpage|raggedright|small|large|Huge|scshape|normalsize|itshape|bfseries)\b\*?", " ", s)
    s = re.sub(r"\\begin\{[^}]*\}(?:\[[^\]]*\])?(?:\{[^}]*\})?|\\end\{[^}]*\}", " ", s)
    s = re.sub(r"\\(?:resumeSubHeadingListStart|resumeSubHeadingListEnd|resumeItemListStart|resumeItemListEnd)", " ", s)
    s = re.sub(r"\\(?:textbf|textit|emph|underline|small|section|resumeItem|resumeSubItem|resumeProjectHeading|"
               r"resumeSubheading|resumeSubSubheading|item|textsc|text)\b\*?", " ", s)
    for k, v in _ESC.items():
        s = s.replace(k, v)
    s = re.sub(r"\$\|\$", "|", s)
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
    s = re.sub(r"[{}]", " ", s)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


@dataclass
class Section:
    name: str
    start: int
    end: int
    body: str


def sections(tex: str) -> list[Section]:
    marks = [(m.start(), m.end(), m.group(1)) for m in _SECTION.finditer(tex)]
    end_doc = tex.find("\\end{document}")
    end_doc = len(tex) if end_doc == -1 else end_doc
    out = []
    for i, (st, en, name) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else end_doc
        out.append(Section(name.strip(), st, nxt, tex[en:nxt]))
    return out


def bullets(tex: str) -> list[str]:
    """Plain text of every \\resumeItem, in document order."""
    out, s = [], strip_comments(tex)
    for m in re.finditer(r"\\resumeItem\s*\{", s):
        inner, _ = _take_group(s, m.end() - 1)
        out.append(tex_to_text(inner).replace("\n", " ").strip())
    return out


def project_blocks(body: str) -> list[str]:
    """Split a Projects section body into one block per \\resumeProjectHeading (ends before the next)."""
    idx = [m.start() for m in re.finditer(r"\\resumeProjectHeading", body)]
    if not idx:
        return []
    tail_m = re.search(r"\\resumeSubHeadingListEnd", body)
    stop = tail_m.start() if tail_m else len(body)
    blocks = []
    for i, st in enumerate(idx):
        en = idx[i + 1] if i + 1 < len(idx) else stop
        blocks.append(body[st:en])
    return blocks


SKILL_LINE = re.compile(r"(\\textbf\{([^}]*):\}\s*)([^\n]*?)(\s*\\\\\s*)$", re.M)


def skill_lines(body: str) -> list[tuple[str, list[str]]]:
    return [(m.group(2).strip(), [x.strip() for x in m.group(3).split(",") if x.strip()])
            for m in SKILL_LINE.finditer(body)]
