# Setup

## Requirements
Python 3.11+, Node 20+. Optional: a LaTeX distribution (`latexmk`/`pdflatex`/`xelatex`) and `pdftotext` (poppler).
Without LaTeX, everything works except PDF compilation; `finalize` reports "No LaTeX compiler found".
On macOS: `brew install --cask basictex` (then `sudo tlmgr install latexmk preprint enumitem titlesec marvosym fancyhdr`) and `brew install poppler`.

## Install
```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
cd frontend && npm install && npm run build && cd ..
cp .env.example .env            # then edit
python scripts/import_master.py ~/Documents/GitHub/Quant-Journal/V2.0/10-Resume-Wiki/main.tex
```
`git pull` Quant-Journal before syncing; the wiki is read from `WIKI_PATH`.

## Run
```bash
cd backend && ../.venv/bin/uvicorn app.main:app --port 8000     # API + built dashboard at http://localhost:8000
cd frontend && npm run dev                                       # dev UI at :5173 with API proxy
python scripts/resume.py sync | scan | jobs
```
The scheduler (scan every `JOB_SCAN_INTERVAL_HOURS`, wiki sync every `WIKI_SYNC_INTERVAL_HOURS`) starts with the API.
Set `SCHEDULER_ENABLED=false` to run manually, or run `python scripts/resume.py scan` from cron / GitHub Actions.

## Tailoring a resume for one job (Claude Code session)
1. Dashboard job page -> **Generate resume** (or `python scripts/resume.py prepare <job_id>`).
2. In Claude Code, open the printed folder and ask: "Follow TAILOR.md and tailor resume.tex".
3. `python scripts/resume.py finalize <job_id>` -> read `ats_report.md` and `changes.md`.
4. Approve in the Resume Center (or `approve <job_id>`); `--force` only for claims you can personally stand behind.

## Credentials (all optional)
| Integration | How |
|---|---|
| Telegram | @BotFather -> token; message the bot; chat id from `https://api.telegram.org/bot<token>/getUpdates` |
| Email | SMTP host/port, address, app password (Gmail: app password) |
| WhatsApp | Official Cloud API only; `WHATSAPP_ENABLED=true` plus token, phone number id, recipient. Pricing and template rules apply |
| GitHub token | Not needed for the local wiki |

## Tests
`cd backend && ../.venv/bin/python -m pytest` and `cd frontend && npx vitest run`.

## Quotas and limits
All job sources are free public JSON APIs (Greenhouse, Lever, Ashby) with no key; the scan makes one request per
company, with retry and backoff. Telegram is free. Gmail SMTP is free within Google's daily limits. Services may change
terms; nothing here requires a paid plan. Deployment: a small VPS or your laptop with the scheduler; a GitHub Actions
cron running `scripts/resume.py scan` also works but needs the database persisted (artifact or repo branch).
