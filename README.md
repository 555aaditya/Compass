# Compass

A personal career assistant: it finds fresher / 0-2 year engineering jobs (India and India-eligible remote),
scores them against what your own Quant-Journal wiki can prove, notifies you, and prepares a truthful,
ATS-checked LaTeX resume per job. **It never submits an application.**

- **Discovery**: Greenhouse, Lever and Ashby public APIs over an editable company watchlist; deterministic
  eligibility (seniority, experience, India location, freshness), dedup, source health.
- **Candidate intelligence**: syncs `Quant-Journal/V2.0/10-Resume-Wiki` into evidence-backed claims with source links,
  change detection and snapshots. Compass itself is excluded from candidate evidence.
- **Matching**: explainable 0-100 score (configurable weights), matching and missing skills, relevant work, emphasis.
- **Resume engine**: workspace + keyword matrix + evidence pack for a Claude Code tailoring session, then compile,
  PDF text validation, keyword-coverage report, change report, claim guard, approval gate.
- **Notifications**: Telegram, email (SMTP), optional official WhatsApp Cloud API; deduplicated, rate-limited.
- **Dashboard**: overview, job feed with filters, job detail, resume center, candidate profile, settings.

Start with [docs/SETUP.md](docs/SETUP.md). Design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
What works and what does not: [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md).
The original product brief is kept in [docs/PROMPT.md](docs/PROMPT.md).
