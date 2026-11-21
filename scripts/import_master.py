#!/usr/bin/env python3
"""Copy a master LaTeX resume (plus assets) into resumes/master/ and record its hash.

The copy is made read-only. The application verifies the hash before every generation and never
writes to this directory. Usage: python scripts/import_master.py /path/to/main.tex
"""
import hashlib
import json
import shutil
import stat
import sys
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / "resumes" / "master"
EXTS = {".tex", ".sty", ".cls", ".bib", ".png", ".jpg", ".jpeg", ".pdf", ".ttf", ".otf"}


def main(src: str) -> None:
    main_tex = Path(src).expanduser().resolve()
    if not main_tex.is_file():
        sys.exit(f"not a file: {main_tex}")
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {"main": "main.tex", "source": str(main_tex), "files": {}}
    for f in [main_tex, *sorted(p for p in main_tex.parent.iterdir() if p.is_file() and p.suffix in EXTS and p != main_tex
                                and " " not in p.name)]:
        target = DEST / ("main.tex" if f == main_tex else f.name)
        if target.exists():
            target.chmod(stat.S_IWUSR | stat.S_IRUSR)
        shutil.copy2(f, target)
        target.chmod(stat.S_IRUSR | stat.S_IRGRP)
        manifest["files"][target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Imported {len(manifest['files'])} file(s) into {DEST}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
