# How to Configure Your Job Alerts

The Launchpad Job Alert System is entirely driven by two simple configuration files: `config.yaml` and `companies.json`. You do not need to modify any Python code to change what jobs you receive.

---

## 1. Modifying `config.yaml`

This file controls **who you are** and **what you're looking for**. Any changes saved here are instantly applied on the next background scrape (which happens every 30 minutes).

### A. Defining Roles & Titles
Under the `roles` section, you define what makes a job a "match":

- **`titles`**: Broad job titles to match against. If a job title contains any of these, it passes the first check.
  ```yaml
  titles:
    - "Software Engineer"
    - "Backend Developer"
  ```
- **`include_keywords`**: Secondary keywords. Even if the title isn't an exact match above, if it contains one of these, it gets flagged for review.
  ```yaml
  include_keywords:
    - "junior"
    - "entry level"
  ```
- **`exclude_keywords`**: **(Highly Important)** Any job containing these words in the title will be *immediately discarded*. Use this to filter out senior roles if you are junior, or vice versa.
  ```yaml
  exclude_keywords:
    - "senior"
    - "staff"
    - "manager"
  ```

### B. Setting Locations
Under `locations`, you can easily toggle geographic regions:
- **`remote: true`**: Automatically captures any role explicitly listed as Remote.
- **`india` / `international`**: Add or remove specific cities and countries under the respective arrays. The script checks if the job location string contains any of these city/country names.

### C. Alerts & Thresholds
- **`email`**: The recipient address where the digest is sent.
- **`min_score`**: (Currently disabled as all matching jobs get a perfect score).
- **`batch_window_minutes`**: Set this to match your background server run schedule (default is 30 minutes) to avoid duplicate email threading.

---

## 2. Modifying `companies.json`

This file tells the system **which companies to track** and **where to find their jobs**.

If you want to add a new company to your tracker, you must add a JSON object to this list. The system supports three specific Applicant Tracking Systems (ATS): `lever`, `greenhouse`, and `ashby`.

### Example Entry:
```json
{
  "name": "Databricks",
  "ats": "greenhouse",
  "source_url": "https://boards.greenhouse.io/databricks"
}
```

### How to add a new company:
1. Go to the target company's "Careers" or "Open Roles" page.
2. Click on a specific open role to view the job description.
3. Look at the URL in your browser's address bar. This will tell you their ATS:
   - If the URL starts with `jobs.lever.co/companyname`, their ATS is **`lever`**.
   - If the URL starts with `boards.greenhouse.io/companyname`, their ATS is **`greenhouse`**.
   - If the URL starts with `jobs.ashbyhq.com/companyname`, their ATS is **`ashby`**.
4. Add the company to `companies.json` using the company name as it appears in the URL (the "board token") appended to the source URL.

> [!NOTE]  
> If the URL does not contain Lever, Greenhouse, or Ashby (e.g. Workday or a completely custom career portal), the current fast-scraping system will ignore it to preserve performance and avoid bot detection. You can still rely on the `remotive` and `linkedin_rss` generic scrapers to occasionally catch those!
