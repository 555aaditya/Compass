"""LaTeX compilation without a shell: argument lists only, no shell-escape, bounded runtime."""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

COMPILERS = ["latexmk", "pdflatex", "xelatex"]


@dataclass
class CompileResult:
    ok: bool
    compiler: str | None
    log: str
    pdf: Path | None = None
    errors: list[dict] | None = None


def detect_compiler(preferred: str | None = None) -> str | None:
    for c in ([preferred] if preferred else []) + COMPILERS:
        if c and shutil.which(c):
            return c
    return None


def parse_errors(log: str) -> list[dict]:
    out = []
    for m in re.finditer(r"^(?:(?P<file>[^\s:]+\.tex):(?P<line>\d+): )?! (?P<msg>.+)$", log, re.M):
        line = m.group("line")
        if not line:
            ln = re.search(r"^l\.(\d+)", log[m.end():m.end() + 400], re.M)
            line = ln.group(1) if ln else None
        out.append({"file": m.group("file") or "resume.tex", "line": int(line) if line else None, "message": m.group("msg")})
    return out


def compile_tex(directory: Path, main: str = "resume.tex", compiler: str | None = None, timeout: int = 120) -> CompileResult:
    comp = detect_compiler(compiler)
    if comp is None:
        return CompileResult(False, None, "No LaTeX compiler found (tried latexmk, pdflatex, xelatex). "
                                          "Install MacTeX/TeX Live or BasicTeX and re-run finalize.")
    if comp == "latexmk":
        cmd = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", main]
    else:
        cmd = [comp, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", main]
    try:
        p = subprocess.run(cmd, cwd=directory, capture_output=True, text=True, timeout=timeout, check=False)
        log = (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return CompileResult(False, comp, f"Compilation timed out after {timeout}s")
    pdf = directory / (Path(main).stem + ".pdf")
    ok = p.returncode == 0 and pdf.exists()
    return CompileResult(ok, comp, log[-8000:], pdf if ok else None, None if ok else parse_errors(log))
