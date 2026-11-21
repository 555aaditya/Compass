# Architecture

Compass is a personal job-discovery and resume-tailoring system. It never submits applications.

## Inspection findings (Phase 1)

### Old Compass implementation (`origin/Dev`)
A flat Python script project: `scrapers/ats/{greenhouse,lever,ashby}.py`, a Remotive and a LinkedIn-RSS scraper,
`matcher/scorer.py` (a hard filter plus a dummy score of 10), an email notifier, `server.py` and a JSON seen-jobs file.

| Kept or reworked | Discarded |
|---|---|
| Greenhouse and Lever endpoints (reworked: retries, typed `RawJob`, HTML cleanup, real dates) | LinkedIn RSS scraping (fragile, against the brief) |
| Ashby: replaced the internal GraphQL call with the official public posting API | The 5000-char description truncation, bare `except: pass`, `print` logging |
| Company watchlist idea (now a DB table, health-tracked, editable) | JSON-file persistence, the dummy scorer, `international.enabled` defaults |
| Email notification idea (now SMTP + Telegram + WhatsApp, deduplicated) | Hard-coded config, the `schedule`-style loop, the static React mock |

Compass is **product context only**. The wiki page `projects/compass.md` is excluded from candidate evidence by
configuration (`WIKI_PRODUCT_CONTEXT_PAGES`), so Compass's technologies never enter the candidate profile.

### Quant-Journal and its "Wiki"
Quant-Journal has no GitHub Wiki. The knowledge base is the local folder `V2.0/10-Resume-Wiki/`:
`profile.md`, `skills.md` (skill, depth ●/●●/●●●, evidence), `projects/*.md` (front matter, tagged bullets, JD keywords),
`experience/oaknorth*.md` (with "Claims to NOT make"), `resume-audit.md` (main.tex checked line by line) and `main.tex`.
The sync module reads this folder. Learning plans elsewhere in the repo (roadmaps, CP trackers) are intentionally not
treated as achievements.

### Master resume
`main.tex` is a single-column Jake-style template with `\pdfgentounicode=1`: already ATS-friendly, so layout is left
alone. Its content, however, contains claims the candidate's own audit marks Wrong or Unbacked (for example
"1,000+ employees", "Redis caching", unlisted skills such as Spark/Tableau). The claim guard enforces that audit.

## Components

```
backend/app/
  models/            SQLAlchemy entities (SQLite now, PostgreSQL-portable)
  services/
    candidate_profile/  wiki_parser (markdown -> Evidence), sync (change detection, snapshots)
    job_discovery/      adapters (Greenhouse, Lever, Ashby), store (dedup), scan (orchestration), watchlist
    job_matching/       eligibility (hard filters), requirements, vocab, candidate_index, scoring
    resume_tailoring/   workspace, keyword_matrix, baseline, guard, latex, compile, service
    ats_analysis/       validator (PDF checks), report (coverage), diff (change report)
    notifications/      channels (Telegram, email, WhatsApp), service (policy, dedup, retries)
    applications/       manual status tracking
  workers/           pipeline (scan -> resumes -> notify), scheduler (APScheduler)
  api/routes.py      REST API       cli.py  manual runs
frontend/            React + TypeScript + Tailwind dashboard (Vite)
```

### Data flow
1. **Wiki sync**: scan wiki -> SHA-256 per page -> new/modified/deleted -> parse -> upsert claims by hash key
   (dedup) -> mark vanished claims deleted -> snapshot the profile when anything changed.
2. **Scan**: per enabled company, adapter -> `RawJob` -> deterministic eligibility -> (kept) upsert with dedup
   (`company + normalised title + primary location`, plus source id and URL) -> requirement extraction -> score.
   One company failing never aborts the scan; vanished postings are expired.
3. **Match**: weights are configurable (default 30/20/20/15/10/5). Hard rejections are never overridden; uncertain
   eligibility caps the score at 84 and is never notified.
4. **Resume**: `prepare` builds `resumes/generated/<company>/<job_id>/` with a baseline copy of the master
   (disputed skills removed, skills and projects ordered by relevance), `keyword_matrix.json`, `evidence_pack.md`,
   and `TAILOR.md`. A Claude Code session edits `resume.tex`; `finalize` compiles, extracts text, validates, and writes
   `ats_report.{json,md}`, `changes.md`, `extracted_resume.txt`. Approval is blocked while error-level claims remain.
5. **Notify**: eligible jobs at or above the threshold, once per channel, daily limit, 3 retries with backoff.

### Why no built-in LLM
Tailoring runs in Claude Code sessions chosen by the user, so the app has no LLM provider dependency and no API
cost. Everything that must be reliable (eligibility, dedup, scoring, validation, claim guard) is deterministic code.

## Security and integrity
- Secrets only from environment; redacted in logs and in `/api/settings`; Telegram errors never include the bot URL.
- The master resume is imported once (hash manifest), stored read-only and git-ignored, verified before every use.
- Resume paths are built from slugs and checked to stay inside the generated root; the file API uses a whitelist.
- LaTeX is compiled with an argument list (no shell), `-no-shell-escape`, a timeout, in the generated copy only.
- Wiki and job text is parsed, never executed or used as instructions.
