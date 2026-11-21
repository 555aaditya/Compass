# Implementation status

Verified 2026-11-22. Backend: 78 pytest tests. Frontend: 4 vitest tests, `tsc` clean, production build succeeds.

## Implemented and tested
| Area | Notes |
|---|---|
| Wiki sync | New/modified/deleted detection, dedup, snapshots, dynamic categories, ambiguous pages flagged, product-context exclusion. Also run against the real wiki (25 pages) |
| Source adapters | Greenhouse, Lever, Ashby against mocked HTTP; retries, 404, 5xx. Also run live against the public APIs |
| Eligibility | Seniority, non-engineering and support roles, experience parsing, India / remote / foreign locations, freshness, unpaid |
| Dedup and scan | Cross-source dedup, per-company failure isolation, expiry, rejection reasons per source |
| Scoring | Weighted, capped when uncertain, matching/missing/blocked skills, relevant work, emphasis |
| Resume workspace | Master protection (hash manifest, read-only), path safety, versions, keyword matrix, evidence pack, baseline (skill pruning, project ordering) |
| Claim guard | Built from the wiki's own audit; run against the real master resume |
| ATS validation | 12 checks exercised on generated PDFs (healthy, missing text, reordered, no contact, layout risks, bad headings) |
| Notifications | Dedup, threshold, uncertain never sent, daily limit, retries, token never leaked; Telegram, SMTP and WhatsApp via mocks |
| API and dashboard | Filtering, sorting, status updates, settings persistence, approvals, file whitelist; Jobs page behaviour |
| Scheduling | APScheduler wired in; interrupted-run recovery. Booting the app and running migrations was checked manually |

## Implemented but not verified end to end
- **LaTeX compilation**: verified 2026-11-22 with BasicTeX + latexmk + pdftotext on the real master (2 pages, 12 of 13
  checks pass, 38/38 skills and 12 links extracted). BasicTeX needs `preprint` (provides `fullpage.sty`) plus
  `latexmk enumitem titlesec marvosym fancyhdr`. Note `~/Library/texlive` user tree was used because `sudo tlmgr` was unavailable.
- **Real Telegram / SMTP / WhatsApp delivery**: needs your credentials; only mocked.
- **Docker image**: written, never built.
- **Dashboard in a browser**: built and type-checked; component test only, no manual click-through.

## Known limitations
- **Few openings**: a live scan on 2026-11-22 over 14 boards (Stripe, Databricks, Razorpay, Groww, ...) kept almost nothing,
  because most postings are senior, non-engineering or outside India. That is the filter working, not a bug, but yield
  is low. More sources (Wellfound, Y Combinator, India-focused boards) are the next step.
- **No public API** for Google, Microsoft, Amazon, Atlassian, Adobe, Salesforce, Oracle, NVIDIA, Uber, Intuit,
  Flipkart, PhonePe, Swiggy, Zomato, Zepto, Postman, BrowserStack, Zoho, Juspay, Chargebee, Hasura (listed, disabled).
  Add them from Settings if you find a Greenhouse/Lever/Ashby board for them.
- Experience and skill extraction is regex/vocabulary based. It is explainable but misses terms outside the vocabulary
  (`job_matching/vocab.py`).
- Link checking is structural (annotations), not live HTTP.
- Bullet rewriting is not automated; it happens in your Claude Code session, then is validated.
- Master resume claims that the wiki audit marks Wrong are reported, not auto-fixed. Fix `main.tex` in Quant-Journal
  and re-import.
- No Wellfound / YC adapter, no GitHub-API wiki mode (local checkout only), no resume side-by-side diff view in the UI
  (the `changes.md` report is downloadable).

## Update 2026-11-22
- Master resume edited in Quant-Journal (uncommitted there): GenAI Analyst title, project claims reworded per the audit, unevidenced skills removed,
  backed skills added, new OakNorth bullets, stray `\newpage` removed. Compiles to 2 pages; 0 error-level claims.
- `resumes/claim_overrides.json`: claims the candidate personally stands behind. Reported as "accepted", never blocking. Review before interviews.
- `.github/workflows/scan.yml`: scheduled scan + Telegram from GitHub Actions (untested). Resume tailoring stays local.
- `POST /api/jobs/manual`: add leads from X / LinkedIn posts by hand. No X or LinkedIn scraping (API is paid / against ToS).
- Watchlist widened to 69 boards (Greenhouse, Lever, Ashby, SmartRecruiters). A live scan then kept 6 jobs; remaining India-fresher yield is genuinely low.
