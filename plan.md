# Launchpad Deployment & Configuration Plan

This document outlines how to move your local job alert system to a 24/7 cloud environment using GitHub Actions, configure your tracking preferences, and safely manage future updates using Pull Requests.

---

## 1. Configuring Your Filters

Before moving to the cloud, ensure your job tracking preferences are accurately mapped out in your configuration files.

### A. Roles, Locations, and Rules (`config.yaml`)
- **Job Titles**: Add the exact title snippets you want to match in the `roles.titles` array (e.g., `"Software Engineer"`, `"Data Scientist"`).
- **Keywords**: Add broad keywords in `include_keywords` to capture non-standard titles (e.g., `"Entry Level"`, `"Junior"`).
- **Exclusions**: Strongly filter out roles using `exclude_keywords` (e.g., `"Senior"`, `"Manager"`, `"Director"`). If a job contains these, it is immediately dropped.
- **Locations**: Enable or disable countries/cities. Toggle `remote: true` to ensure remote roles are always included.

### B. Tracking Companies (`companies.json`)
Add new target companies by creating a new block in `companies.json`:
```json
{
  "name": "Databricks",
  "ats": "greenhouse",
  "source_url": "https://boards.greenhouse.io/databricks"
}
```
*Note: Currently supported ATS platforms are `lever`, `greenhouse`, and `ashby`.*

---

## 2. 24/7 Cloud Deployment (GitHub Actions)

Running the server locally means it shuts off when your laptop sleeps. Moving it to GitHub Actions keeps it running 24/7 for free.

### Step-by-Step GitHub Actions Setup
1. **Create the Workflow File**: We will create `.github/workflows/launchpad.yml`. This file tells GitHub to run `main.py` every 30 minutes using a scheduled cron job.
2. **Push to a Private Repo**: Commit your entire `Compass` repository (excluding the `venv` folder and `.env` file) and push it to a private repository on GitHub.
3. **Configure Repository Secrets**: 
   - Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
   - Add a New Repository Secret: Name it `RESEND_API_KEY` and paste your Resend API key as the value.
4. **Automated State Tracking**: The GitHub Action will automatically commit updates to `data/seen_jobs.json` back to your repository so it remembers which jobs it has already sent you.

---

## 3. Step-by-Step Deployment via Pull Requests

To keep your main tracker stable, any new features, scrapers, or configuration updates should be deployed using Pull Requests. 

### Phase 1: Local Development
1. **Branch Out**: Create a new branch for your update (`git checkout -b update-companies`).
2. **Make Changes**: Add a new company to `companies.json` or tweak your `config.yaml`.
3. **Test Locally**: Run `python main.py` on your laptop to verify the script doesn't crash and correctly identifies the new jobs.

### Phase 2: Pull Request (PR)
1. **Commit & Push**: 
   ```bash
   git add companies.json
   git commit -m "Added Databricks to tracking list"
   git push origin update-companies
   ```
2. **Open a PR**: Go to GitHub and open a Pull Request from `update-companies` into your `main` branch.
3. **Review**: Check the file diffs in the PR to ensure no accidental typos or syntax errors were introduced in the JSON/YAML files.

### Phase 3: Merging & Production
1. **Merge the PR**: Once approved, click "Merge Pull Request".
2. **Cloud Sync**: Your `main` branch is now updated. The next time the 30-minute GitHub Action cron schedule triggers, it will pull the latest `main` branch, recognizing your newly added companies or updated filters!
