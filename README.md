<div align="center">

# Compass

**Find the jobs you can actually win. Apply with a resume that tells the truth.**

A personal career assistant. It scans company job boards for fresher and 0-2 year engineering roles in India,
scores each one against what your own notes can prove, and prepares an ATS-checked LaTeX resume for the ones worth
applying to. It never submits an application.

[![Scan](https://github.com/555aaditya/Compass/actions/workflows/scan.yml/badge.svg)](https://github.com/555aaditya/Compass/actions/workflows/scan.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12-3776ab)
![React](https://img.shields.io/badge/react-18-61dafb)

[**Live jobs page**](https://555aaditya.github.io/Compass/) ·
[Install](#install) ·
[Setup](docs/SETUP.md) ·
[Architecture](docs/ARCHITECTURE.md) ·
[ATS guide](docs/ATS_GUIDE.md) ·
[API](docs/API.md) ·
[Roadmap](#roadmap)

```sh
python3 scripts/resume.py scan
```

</div>

---

Job hunting is mostly repetition: open the same career pages, skim hundreds of senior and non-engineering roles,
guess whether you fit, then rewrite a resume by hand. The risky part is the rewriting. A resume tuned to a job
description drifts toward claims you can't defend in an interview.

Compass automates the repetition and keeps the claims honest. It reads a knowledge base you already maintain (a folder
of markdown notes about your skills, projects and work), turns it into evidence with source links, and uses only that
evidence to score jobs and to tailor resumes. A skill you can't back up is reported as a gap, never added to a
resume. You review a short report and a diff instead of re-reading everything.

> **Status: working, personal, early.** The scan, scoring, resume pipeline, Telegram alerts and dashboard run end to
> end and are tested (80 backend tests, 4 frontend tests). The scheduled GitHub Actions scan has run successfully.
> Real SMTP and WhatsApp delivery, and the Docker image, are untested. See
> [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) for what is and isn't verified.

## What it looks like

A Telegram alert, sent once per job when it scores 70 or more and is eligible:

```
[Strong 80] Data Engineer I, Business Data Technologies at Amazon

Company: Amazon
Location: Hyderabad, Telangana, IND (onsite)
Experience: fresher / 0+ years
Match score: 80/100
Why: Matches AWS, Python, SQL, PostgreSQL; Relevant work: <your projects>
Matching skills: AWS, Python, SQL, PostgreSQL, ETL
Missing skills: Spark
Tailored resume: prepared (compiled), awaiting approval
Apply: https://www.amazon.jobs/en/jobs/...
```

A resume workspace, one folder per job:

```
resumes/generated/<company>/<job_id>/
  TAILOR.md            instructions for the Claude Code session that edits the resume
  resume.tex           baseline copy of your master, ready to edit
  keyword_matrix.json  each requirement -> your evidence -> include, emphasize or do not claim
  evidence_pack.md     the wiki excerpts you are allowed to draw on
  job_context.json     match_analysis.json
  -- after `finalize` --
  resume.pdf           ats_report.md      changes.md      extracted_resume.txt
```

## Install

Requirements: Python 3.11+ and Node 20+. For PDFs, a LaTeX distribution and `pdftotext` (BasicTeX and poppler on
macOS).

```sh
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
(cd frontend && npm install && npm run build)
cp .env.example .env                                   # then edit
python3 scripts/import_master.py path/to/main.tex      # your master LaTeX resume, kept read-only
```

The full guide, including LaTeX packages and credentials, is in [`docs/SETUP.md`](docs/SETUP.md).

## Quick start

```sh
python3 scripts/resume.py sync        # read your wiki into the candidate profile
python3 scripts/resume.py scan        # fetch jobs, filter, score, prepare resumes, send alerts
python3 scripts/resume.py jobs        # list the best matches
cd backend && ../.venv/bin/uvicorn app.main:app --port 8000   # dashboard at http://localhost:8000
```

Tailor a resume for one job:

```sh
python3 scripts/resume.py prepare 12     # build the workspace
# in Claude Code: "Follow TAILOR.md and tailor resume.tex"
python3 scripts/resume.py finalize 12    # compile, validate, report
python3 scripts/resume.py approve 12     # blocked while claims contradict your evidence
```

## Commands

| Command | What it does |
|---|---|
| `sync` | Reads the wiki, detects new, changed and deleted pages, updates the evidence, snapshots the profile |
| `scan` | Fetches every enabled board, applies eligibility rules, deduplicates, scores, prepares resumes, notifies |
| `jobs` | Lists active jobs by score |
| `prepare <id>` | Creates the per-job workspace from your master resume and evidence |
| `finalize <id>` | Compiles the LaTeX, extracts PDF text, runs the ATS checks, writes the reports |
| `approve <id>` | Marks a resume final; refuses while error-level claims remain (`--force` if you vouch for them) |
| `snapshot` | Writes a read-only static jobs page |

## How a job is scored

Hard filters run first and are never overridden: seniority, experience over the limit, location outside India,
non-engineering and support roles, unpaid, stale. What passes is scored out of 100, with weights you can change in
Settings.

| Criterion | Default weight |
|---|---:|
| Technical skill match (required skills count more than preferred) | 30 |
| Role relevance | 20 |
| Experience compatibility | 20 |
| Projects and achievements | 15 |
| Location | 10 |
| Freshness | 5 |

A job with uncertain eligibility is capped at 84 and never triggers an alert. Every score keeps its breakdown,
matching and missing skills, and the work that supports it.

## The truthful resume pipeline

`job description -> requirements -> your evidence -> baseline resume -> your edits -> PDF -> ATS checks -> report`

- **Claim guard.** Your own audit of your resume (lines marked wrong or unbacked, and a do-not-list of skills) is
  parsed into rules. Resume text that contradicts it is an error and blocks approval. Claims you decide to stand
  behind go in a local override file and show as "accepted" in reports.
- **ATS checks.** Text extracts, standard headings, contact details, skills readable, dates, no replacement
  characters, bullets in order and matching the source, links present, layout risks, page count. This catches a PDF
  that looks right but extracts wrongly.
- **Keyword coverage** is an internal diagnostic. It is not an ATS score and does not predict whether any employer's
  system will select a resume.
- **Your master resume is read-only.** It is imported once with a hash, git-ignored, verified before every use and
  never edited. Generated resumes live beside it.

## Where jobs come from

| Source | Boards | Notes |
|---|---:|---|
| Greenhouse, Lever, Ashby, SmartRecruiters | 70 | Public job-board APIs, one request per company, retry with backoff |
| Amazon, Atlassian | 2 | Their own public career feeds |
| Blocked or no public feed | 18 | Google, Microsoft, Adobe, Salesforce, Oracle, NVIDIA, Uber, Intuit, Flipkart, PhonePe and others. Workday sites answer non-browser clients with HTTP 429, and Compass does not evade that. The dashboard links to a pre-filtered search for each |
| Manual leads | any | `POST /api/jobs/manual` scores a posting you found elsewhere |

LinkedIn and X are not scraped: LinkedIn forbids it and X's API is paid. Add companies, change priorities and watch
per-source health in Settings.

## Runs without your computer

`.github/workflows/scan.yml` runs the scan at 09:00 and 21:00 IST, sends Telegram alerts, and publishes a read-only
jobs page to GitHub Pages. The page shows company, role, location, score and date only, nothing derived from your
notes. The database lives in the Actions cache, and your wiki is read with a repository secret. Secrets needed:
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `QUANT_JOURNAL_TOKEN`. Resume tailoring stays on your machine.

## Dashboard

Overview, job feed with filters and sorting, job detail with the match explanation, resume center (finalize,
approve, ATS report, change report, PDF), candidate profile with source links, and settings for preferences, weights,
channels and the company watchlist.

## What Compass is, and isn't

- **It doesn't apply for you.** It never submits an application. You review everything and apply yourself.
- **It doesn't write your resume from nothing.** Bullet rewriting happens in your Claude Code session, under rules,
  and is validated afterwards. There is no LLM key and no API cost in the app.
- **It isn't a guarantee.** Few postings fit a 0-2 year profile in India at any moment, so expect a short list.
  The filters are strict on purpose.
- **Its extraction is a vocabulary, not magic.** Skills outside `backend/app/services/job_matching/vocab.py` are
  missed. The result is explainable and easy to extend.

## Roadmap

| Step | What | Status |
|---|---|---|
| Wiki sync and candidate profile | Evidence with sources, snapshots, change history | **Done** |
| Job discovery | 5 source types, eligibility filters, dedup, source health | **Done** |
| Matching | Explainable score, gaps, relevant work | **Done** |
| Resume engine | Workspace, claim guard, compile, ATS checks, reports, approval | **Done** |
| Notifications | Telegram verified; SMTP and WhatsApp mock-tested | Telegram **Done** |
| Dashboard | Six pages | **Done** |
| Scheduled scan and read-only page | GitHub Actions | **Done** |
| Email-alert intake | Read job alerts that blocked sites send by email | Planned |
| More India-focused sources | Boards that publish a public feed | Planned |
| Side-by-side resume diff in the UI | `changes.md` exists today | Planned |

## Licence

MIT. See [`LICENSE`](LICENSE).
