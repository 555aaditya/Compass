"""Build tiny but valid text PDFs (with link annotations) so ATS validation can be tested without LaTeX."""
from pathlib import Path


def make_pdf(path: Path, lines: list[str], links: list[str] | None = None, pages: int = 1) -> Path:
    def esc(t: str) -> str:
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objs: list[str] = []
    n_pages = pages
    per = max(1, -(-len(lines) // n_pages))
    page_ids, content_ids = [], []
    # object numbering: 1 catalog, 2 pages, 3 font, then per page: page, content, annots
    nid = 4
    chunks = [lines[i * per:(i + 1) * per] for i in range(n_pages)]
    body = {}
    for ci, chunk in enumerate(chunks):
        pid, cid = nid, nid + 1
        nid += 2
        annots = []
        if ci == 0 and links:
            for u in links:
                body[nid] = (f"<< /Type /Annot /Subtype /Link /Rect [72 700 200 720] /Border [0 0 0] "
                             f"/A << /S /URI /URI ({esc(u)}) >> >>")
                annots.append(nid)
                nid += 1
        stream = "BT /F1 10 Tf 72 760 Td 12 TL " + " ".join(f"({esc(t)}) Tj T*" for t in chunk) + " ET"
        body[cid] = f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"
        ann = f"/Annots [{' '.join(f'{a} 0 R' for a in annots)}]" if annots else ""
        body[pid] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {cid} 0 R "
                     f"/Resources << /Font << /F1 3 0 R >> >> {ann} >>")
        page_ids.append(pid)
    body[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    body[2] = f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {len(page_ids)} >>"
    body[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    out, offsets = "%PDF-1.4\n", {}
    for i in sorted(body):
        offsets[i] = len(out.encode("latin-1"))
        out += f"{i} 0 obj\n{body[i]}\nendobj\n"
    xref = len(out.encode("latin-1"))
    out += f"xref\n0 {max(body) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{offsets[i]:010d} 00000 n \n" for i in range(1, max(body) + 1))
    out += f"trailer\n<< /Size {max(body) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    path.write_bytes(out.encode("latin-1"))
    return path
