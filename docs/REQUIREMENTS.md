# Launchpad — Job Alert System
## Requirements: Real-Time Role Discovery & Email Alerts

---

## What It Does

Monitors every major job source — ATS platforms, job boards, company career pages —
and emails you the moment a matching role opens. Fully configurable. No dashboard,
no complexity. Just: new role opens → you get an email.

---

## 1. Configuration File

Everything lives in one file: `config.yaml`
You edit this file to change anything. No code changes needed.

```yaml
# ─── WHO YOU ARE ──────────────────────────────────────────
email: "555aaditya@proton.me"

# ─── ROLES ────────────────────────────────────────────────
roles:
  titles:
    - "Software Engineer"
    - "SWE"
    - "Backend Engineer"
    - "Frontend Engineer"
    - "Full Stack Engineer"
    - "Data Engineer"
    - "ML Engineer"
    - "Data Scientist"
    - "AI Engineer"
    - "Research Engineer"

  include_keywords:
    - "junior"
    - "entry level"
    - "new grad"
    - "graduate"
    - "0-2 years"
    - "fresher"
    - "associate"

  exclude_keywords:
    - "senior"
    - "staff"
    - "principal"
    - "lead"
    - "manager"
    - "director"
    - "5+ years"
    - "7+ years"
    - "10+ years"

# ─── EXPERIENCE ───────────────────────────────────────────
experience:
  min_years: 0
  max_years: 2

# ─── LOCATIONS ────────────────────────────────────────────
locations:
  remote: true          # include remote / work from anywhere

  india:
    enabled: true
    cities:
      - Bangalore
      - Hyderabad
      - Pune
      - Mumbai
      - Gurgaon
      - Noida
      - Delhi NCR
      - Chennai

  international:
    enabled: true
    countries:
      - USA
      - UK
      - Ireland
      - Poland
      - Singapore
      - Hong Kong
      - Thailand
      - Australia
      - New Zealand

  unspecified_location: include   # include / exclude / flag

# ─── COMPANIES ────────────────────────────────────────────
# Add or remove freely. Group labels are just for your reference.
companies:

  maang:
    - Google
    - Meta
    - Apple
    - Amazon
    - Netflix

  tier2_product:
    - Microsoft
    - Stripe
    - Uber
    - Airbnb
    - Salesforce
    - LinkedIn
    - Snap
    - Spotify
    - Adobe
    - Atlassian
    - Figma
    - Notion
    - Canva
    - Databricks
    - Snowflake
    - Palantir
    - OpenAI
    - Anthropic
    - Cohere
    - Mistral
    - Hugging Face

  finance:
    - JP Morgan
    - Goldman Sachs
    - Morgan Stanley
    - Citadel
    - Jane Street
    - Two Sigma
    - BlackRock
    - Deutsche Bank
    - HSBC
    - Barclays
    - Revolut
    - Wise

  india_product:
    - Flipkart
    - Meesho
    - Swiggy
    - Zomato
    - PhonePe
    - Razorpay
    - Groww
    - CRED
    - Dream11
    - InMobi
    - Freshworks
    - Zoho
    - Druva
    - Browserstack
    - Postman

# ─── ALERT SETTINGS ───────────────────────────────────────
alerts:
  send_when: "new_roles_only"   # new_roles_only | always
  min_score: 6                  # 1–10, roles below this are skipped
  batch_window_minutes: 30      # collect roles for 30 min then send one email
                                # (avoids getting 20 separate emails at once)
```

---

## 2. Data Sources

Scraped in priority order. If a role appears in multiple sources, deduplicated.

### A. ATS Platforms (Most Reliable — Data Direct from Company)

| ATS | Method | Notes |
|---|---|---|
| **Lever** | Public REST API (`/v0/postings`) | Real-time, clean JSON |
| **Ashby** | Public REST API (`/jobs`) | Real-time, clean JSON |
| **Greenhouse** | Public Board API (`/jobs`) | Real-time, clean JSON |
| **Workday** | Playwright headless scraper | JS-rendered, needs browser |
| **SmartRecruiters** | Public API | Clean JSON |
| **iCIMS** | Playwright headless scraper | |
| **Taleo** | Playwright headless scraper | |
| **Jobvite** | Public XML feed | |
| **BambooHR** | Public JSON API | |
| **Custom / Internal** | Playwright + per-company parser | Google, Meta, Microsoft |

Company → ATS mapping stored in `companies.json`:
```json
[
  {
    "name": "Stripe",
    "ats": "lever",
    "source_url": "https://jobs.lever.co/stripe"
  },
  {
    "name": "Google",
    "ats": "custom",
    "source_url": "https://careers.google.com/jobs/results/"
  }
]
```

### B. Job Boards & APIs

| Source | Method | Free? | Best For |
|---|---|---|---|
| **LinkedIn** | RSS feed (public) | ✅ | Broadest coverage |
| **Indeed** | RSS feed (public) | ✅ | High volume |
| **Adzuna API** | REST API (250 req/day free) | ✅ | India + global SWE |
| **Remotive API** | REST API (unlimited) | ✅ | Remote tech roles |
| **Arbeitnow** | REST API (unlimited) | ✅ | Remote + EU roles |
| **The Muse API** | REST API (unlimited) | ✅ | US tech companies |
| **WellFound (AngelList)** | RSS / scraper | ✅ | Startups |
| **Instahyre** | Scraper | ✅ | India tech roles |
| **Naukri** | Scraper | ✅ | India broad coverage |
| **iimjobs** | Scraper | ✅ | India finance + tech |

### C. Source Priority & Deduplication
- Each job gets a hash of: `company + title + location + url`
- If same hash seen before → skip
- If same role found on both Lever API and LinkedIn → keep one, log both source URLs
- Hashes stored in `data/seen_jobs.json`, expire after 45 days

---

## 3. Matching Logic

### Step 1 — Hard Filters (Fast, no AI)
Applied first to reduce volume before AI scoring:
- Title must contain at least one configured role keyword
- Location must match configured cities, countries, or remote flag
- Must NOT contain any exclude_keywords
- Company must be in configured company list

### Step 2 — AI Relevance Score (Claude API)
For roles that pass hard filters, Claude scores 1–10:

**Input:**
```
Job Title: New Grad Software Engineer
Company: Stripe
Location: Remote
JD Summary: [first 500 words of JD]

Candidate wants: entry-level SWE or Data/ML roles, 0-2 yrs exp,
locations: India cities + USA/UK/Singapore/remote.
```

**Output:**
```json
{
  "score": 8,
  "reason": "Strong title match, remote role, relevant tech stack",
  "seniority_inferred": "new grad",
  "flag": "strong_match"
}
```

Score thresholds (configurable in `config.yaml`):
- 9–10 → 🔥 Strong Match
- 6–8  → ✅ Good Match
- < 6  → Skipped, not emailed

> AI scoring costs ~$0.001 per role. At 200 roles/day filtered down to ~30 for
> scoring, this is under $1/month on Claude API free/low tier.

---

## 4. Email Digest

### Trigger
Sent **only when new matched roles are found**.
Roles batched within a 30-minute window into a single email (configurable).

### Recipient
Pulled from `config.yaml` → `email`

### Sending Service
**Resend** — free tier: 100 emails/day, no credit card needed.
Sign up at resend.com, paste API key into `.env`.

### Email Format (HTML)

```
Subject: 🚀 [7] New Roles — Stripe, Google, JP Morgan | May 20

🔥 STRONG MATCHES
────────────────────────────────────────────
  Stripe          New Grad Software Engineer       Remote
                  Lever · Posted 2h ago            Score 9/10
                  [View Role ↗]

  Google          University Grad SWE              Bangalore, Hybrid
                  Custom · Posted 4h ago           Score 9/10
                  [View Role ↗]

✅ GOOD MATCHES
────────────────────────────────────────────
  JP Morgan       Technology Analyst               Mumbai, On-site
                  Workday · Posted 1h ago          Score 7/10
                  [View Role ↗]

  Anthropic       ML Engineer – New Grad           Remote
                  Ashby · Posted 6h ago            Score 7/10
                  [View Role ↗]

  Revolut         Junior Backend Engineer          Bangalore, Hybrid
                  SmartRecruiters · Posted 3h ago  Score 6/10
                  [View Role ↗]

────────────────────────────────────────────
Skipped (already seen): 12   |   Total monitored: 63 companies
Edit config: config.yaml
```

- Clean, minimal HTML — renders well in ProtonMail
- Every role links directly to the application page
- No images, no tracking pixels

---

## 5. Scheduling

### Option A — Local (Simple)
```bash
python main.py
```
Run manually or via cron:
```
*/30 * * * * cd /path/to/launchpad && python main.py
```
Runs every 30 minutes. Emails only if new roles found.

### Option B — GitHub Actions (Free, Runs in Cloud)
`.github/workflows/launchpad.yml`:
- Runs every 30 minutes via schedule cron
- No server needed — free on GitHub
- Commits updated `seen_jobs.json` back to repo after each run
- Secrets: `ANTHROPIC_API_KEY`, `RESEND_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`

```yaml
on:
  schedule:
    - cron: "*/30 * * * *"
```

---

## 6. File Structure

```
launchpad/
├── main.py                    # Orchestrator — runs full pipeline
├── config.yaml                # YOUR config — roles, companies, locations, email
├── .env                       # API keys (never committed to git)
├── companies.json             # Company → ATS mapping + source URLs
│
├── scrapers/
│   ├── ats/
│   │   ├── lever.py           # Lever public API
│   │   ├── ashby.py           # Ashby public API
│   │   ├── greenhouse.py      # Greenhouse public API
│   │   ├── workday.py         # Workday Playwright scraper
│   │   ├── smartrecruiters.py
│   │   ├── icims.py
│   │   ├── taleo.py
│   │   ├── jobvite.py
│   │   ├── bamboohr.py
│   │   └── generic.py         # Fallback Playwright scraper
│   │
│   └── boards/
│       ├── linkedin_rss.py
│       ├── indeed_rss.py
│       ├── adzuna.py
│       ├── remotive.py
│       ├── arbeitnow.py
│       ├── themuse.py
│       ├── wellfound.py
│       ├── instahyre.py
│       ├── naukri.py
│       └── iimjobs.py
│
├── matcher/
│   └── scorer.py              # Hard filter + Claude AI scoring
│
├── notifier/
│   └── email.py               # Build + send Resend email digest
│
├── data/
│   └── seen_jobs.json         # Deduplication store (auto-managed)
│
├── .github/
│   └── workflows/
│       └── launchpad.yml      # GitHub Actions schedule
│
├── requirements.txt
└── README.md
```

---

## 7. Environment Variables

```env
# Required
ANTHROPIC_API_KEY=sk-...
RESEND_API_KEY=re_...

# Optional (for Adzuna job board API)
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

---

## 8. Setup (3 Steps)

```bash
# 1. Install
pip install playwright requests pyyaml anthropic resend feedparser beautifulsoup4
playwright install chromium

# 2. Configure
nano config.yaml        # set your roles, locations, companies, email
cp .env.example .env
nano .env               # paste your API keys

# 3. Run
python main.py
```

Get free API keys:
- **Anthropic**: platform.anthropic.com (free credits on signup)
- **Resend**: resend.com (free, no credit card)
- **Adzuna**: adzuna.com/api (free, instant approval)

---

## 9. Build Order for Claude Code

```
1. config.yaml schema + loader
2. companies.json with all companies + ATS types
3. scrapers/ats/lever.py       ← easiest, public API
4. scrapers/ats/ashby.py       ← easiest, public API
5. scrapers/ats/greenhouse.py  ← public API
6. scrapers/boards/adzuna.py   ← free API, good coverage
7. scrapers/boards/remotive.py ← unlimited free API
8. scrapers/boards/linkedin_rss.py
9. matcher/scorer.py           ← hard filter + Claude scoring
10. notifier/email.py          ← Resend digest
11. main.py                    ← wire everything together
12. scrapers/ats/workday.py    ← hardest, do last
13. scrapers/ats/generic.py    ← fallback
14. remaining boards           ← naukri, instahyre, iimjobs
15. .github/workflows/launchpad.yml
```

---

## 10. Limitations

| Issue | Mitigation |
|---|---|
| LinkedIn blocks scrapers | RSS feed used instead — no auth needed |
| Naukri / Instahyre rate limits | Polite delays between requests (3–5s) |
| Workday bot detection | Random delays + human-like Playwright behaviour |
| CAPTCHA on some portals | Logged and skipped, not blocked |
| Role posted then deleted quickly | 30-min polling window catches most |
| ATS changes DOM structure | Per-scraper fallback to generic parser |