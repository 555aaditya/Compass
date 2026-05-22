# User Outreach & Acquisition Strategy

To find a list of people who are actively looking for work and might benefit from the Launchpad tool, you can combine a few different sourcing strategies across major platforms. 

---

## 1. GitHub (Easiest for Finding Emails)
GitHub is fantastic because developers often put their email addresses directly in their public profiles.

- **Bio Search Strategy:** Use the GitHub Search API to look for users whose bios contain specific phrases.
  - *Keywords:* "looking for opportunities", "open to work", "seeking new roles", "hire me".
- **Execution:** You can write a Python script using the `requests` library to query `https://api.github.com/search/users?q="open+to+work"`. Iterate through the profiles to extract the public `email` field.

## 2. X / Twitter (Best for Real-Time Intent)
People often tweet immediately after being laid off or when they start their job hunt.

- **Advanced Search Strategy:** Search for high-intent phrases combined with roles.
  - *Queries:* `"looking for a new role" AND "software engineer"`, `"I was affected by the layoffs at"`, `#opentowork`, or `"looking for my next adventure"`.
- **Execution:** Use the X API or tools like **Apify** (which has pre-built Twitter scrapers) to pull tweets matching these queries from the last 7 days. Check their bios for links to portfolios or email addresses.

## 3. Hacker News "Who is looking for work?" Threads
Every single month, Hacker News posts a "Who is looking for work?" thread where hundreds of developers post their resumes, contact info, and availability.

- **Execution:** Search Hacker News for the latest month's thread (e.g., "Ask HN: Who is looking for work? May 2026"). Write a simple BeautifulSoup script to scrape the comments, extract the text, and pull out any email addresses using a regular expression.

## 4. Layoff Alumni Lists (High Empathy Approach)
When large tech companies do layoffs, organizers often put together public Google Sheets of "impacted employees" to help them get hired.

- **Execution:** Websites like **layoffs.fyi** or simple searches on LinkedIn for "alumni list" or "opt-in layoff list" will yield massive spreadsheets filled with names, LinkedIn profiles, and often direct email addresses of people who urgently need a tool exactly like yours.

## 5. LinkedIn (Best Volume, Hardest to Scrape)
LinkedIn is the holy grail for job seekers, but their anti-scraping measures are intense. The best workaround is using **Google Dorks** to index public profiles.

- **Google Dork Strategy:** Paste this exactly into Google:
  `site:linkedin.com/in/ "open to work" "software engineer" -intitle:"profiles"`
- **Execution:** This will return thousands of LinkedIn profiles of software engineers who have "open to work" on their profile. You can use browser extensions like **PhantomBuster** or **Data Miner** to extract these search results into a CSV. Finding emails from LinkedIn profiles usually requires enrichment tools like *Hunter.io*, *Apollo.io*, or *Snov.io*.

---

### 💡 Recommendation
Start with the **GitHub API** and **Hacker News threads**. Since you already have a Python environment set up for Launchpad, these two sources are the easiest to write quick automated scripts for to extract a clean list of emails.
