import os
import json
import hashlib
import time
from scrapers.main_scraper import fetch_all_jobs
from config_loader import COMPANIES
from matcher.scorer import process_jobs
from notifier.email import send_digest

SEEN_JOBS_FILE = "data/seen_jobs.json"

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_seen_jobs(seen_jobs):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(seen_jobs, f)

def get_job_hash(job):
    # Hash based on company, title, location, url
    unique_string = f"{job.get('company','')}-{job.get('title','')}-{job.get('location','')}-{job.get('url','')}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

def main():
    print("Starting Launchpad Job Alert System...")
    
    seen_jobs = load_seen_jobs()
    
    # 1. Scrape all jobs
    print("Scraping jobs from all configured sources...")
    raw_jobs = fetch_all_jobs(COMPANIES, include_boards=True)
    print(f"Total raw jobs fetched: {len(raw_jobs)}")
    
    # 2. Deduplicate
    new_jobs = []
    current_time = time.time()
    
    for job in raw_jobs:
        job_hash = get_job_hash(job)
        if job_hash not in seen_jobs:
            new_jobs.append(job)
            seen_jobs[job_hash] = current_time
            
    print(f"New jobs after deduplication: {len(new_jobs)}")
    
    # Cleanup old seen jobs (e.g., older than 45 days)
    # 45 days in seconds = 45 * 24 * 60 * 60 = 3888000
    seen_jobs = {k: v for k, v in seen_jobs.items() if current_time - v < 3888000}
    save_seen_jobs(seen_jobs)
    
    if not new_jobs:
        print("No new jobs to process. Exiting.")
        return
        
    # 3. Filter and Score
    print("Applying hard filters and AI scoring...")
    matched_jobs = process_jobs(new_jobs)
    print(f"Jobs matching criteria after scoring: {len(matched_jobs)}")
    
    # 4. Notify
    if matched_jobs:
        print("Sending email digest...")
        send_digest(matched_jobs)
    else:
        print("No jobs matched criteria. No email sent.")

if __name__ == "__main__":
    main()
