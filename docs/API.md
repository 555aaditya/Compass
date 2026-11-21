# API (FastAPI, `/api`; interactive docs at `/docs`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/overview` | dashboard counters, last scan / wiki sync, recent notifications |
| GET | `/jobs` | filters: `min_score company work_mode status eligibility max_experience days q active_only`; `sort=score\|newest\|company\|role` |
| GET | `/jobs/{id}` | full detail, analysis, skills, resumes |
| POST | `/jobs/{id}/status` | `{status, note}` manual tracking (`/statuses` lists valid values) |
| POST | `/jobs/{id}/resume` | prepare a resume workspace |
| GET | `/resumes`, `/resumes/{id}/report`, `/resumes/{id}/files/{name}` | list, ATS report, whitelisted files |
| POST | `/resumes/{id}/finalize`, `/resumes/{id}/approve` | compile + validate; approve (`{force}`) |
| GET | `/profile`, `/profile/history` | candidate profile by category, sync history |
| POST | `/profile/evidence/{id}/verification` | correct an uncertain claim |
| GET/PUT | `/settings` | preferences (secrets are never returned) |
| GET/POST/PATCH/DELETE | `/companies` | watchlist |
| POST | `/run/scan`, `/run/wiki-sync` | manual runs (background) |
| GET | `/scans` | scan history with per-source results and rejection reasons |
