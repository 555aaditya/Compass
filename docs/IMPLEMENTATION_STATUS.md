# Implementation status

Verified 2026-11-22. Backend: 72 pytest tests. Frontend: 4 vitest tests, `tsc` clean, production build succeeds.

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
- **LaTeX compilation of a real resume**: no TeX distribution is installed on this machine, so `compile_tex` is only tested
  with mocks and the no-compiler path. Install BasicTeX/MacTeX and run `scripts/resume.py finalize` once.
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
