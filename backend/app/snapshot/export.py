"""Static, read-only jobs page for GitHub Pages / Cloudflare Pages. Jobs only: no profile, resumes or notes."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Compass jobs</title><meta name="robots" content="noindex,nofollow">
<style>:root{color-scheme:light dark;font-family:system-ui,sans-serif}body{margin:0 auto;max-width:1100px;padding:16px}
input,select{padding:6px;margin:0 6px 8px 0}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:6px 8px;border-top:1px solid #8884}
.s{font-weight:600}.excellent{color:#059669}.strong{color:#0284c7}.moderate{color:#d97706}small{color:#888}a{color:#4f46e5}</style></head><body>
<h1>Compass jobs</h1><p><small id="meta"></small></p>
<input id="q" placeholder="Search"><select id="min"><option value="0">Any score</option><option value="70" selected>70+</option><option value="85">85+</option></select>
<select id="el"><option value="">Eligible + uncertain</option><option>eligible</option></select>
<table><thead><tr><th>Score</th><th>Company</th><th>Role</th><th>Location</th><th>Found</th><th>Why</th></tr></thead><tbody id="rows"></tbody></table>
<script>
let D;const $=id=>document.getElementById(id),esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function draw(){const q=$("q").value.toLowerCase(),m=+$("min").value,e=$("el").value;
$("rows").innerHTML=D.jobs.filter(j=>(j.score??0)>=m&&(!e||j.eligibility===e)&&(j.company+j.title+j.location).toLowerCase().includes(q)).map(j=>
`<tr><td class="s ${esc(j.category)}">${Math.round(j.score)}</td><td>${esc(j.company)}</td><td><a href="${esc(j.apply_url)}" rel="noopener noreferrer" target="_blank">${esc(j.title)}</a>${j.eligibility==="uncertain"?" <small>(uncertain)</small>":""}</td><td>${esc(j.location)} <small>${esc(j.work_mode)}</small></td><td>${esc(j.found)}</td><td><small>${esc(j.why)}</small></td></tr>`).join("")}
fetch("jobs.json").then(r=>r.json()).then(d=>{D=d;$("meta").textContent=`Snapshot generated ${d.generated_at} (updates when the scheduled scan runs, not live). ${d.jobs.length} jobs.`;draw()});
["q","min","el"].forEach(i=>$(i).addEventListener("input",draw));
</script></body></html>"""


def export_snapshot(db: Session, out_dir: Path, min_score: float = 40) -> int:
    jobs = db.scalars(select(Job).where(Job.active.is_(True), Job.eligibility.in_(["eligible", "uncertain"]),
                                        Job.score >= min_score).order_by(Job.score.desc())).all()
    rows = [{"company": j.company.name, "title": j.title, "location": j.location, "work_mode": j.work_mode,
             "score": j.score, "category": j.category, "eligibility": j.eligibility, "apply_url": j.apply_url,
             "found": j.first_seen_at.strftime("%Y-%m-%d"), "why": "; ".join(j.analysis.get("why_matches", []))[:200]}
            for j in jobs]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "jobs.json").write_text(json.dumps({"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                                                   "jobs": rows}, indent=1))
    (out_dir / "index.html").write_text(PAGE, encoding="utf-8")
    return len(rows)
