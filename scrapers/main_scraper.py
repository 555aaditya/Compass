from scrapers.ats.lever import scrape_lever
from scrapers.ats.greenhouse import scrape_greenhouse
from scrapers.ats.ashby import scrape_ashby
from scrapers.boards.remotive import scrape_remotive
import json

def fetch_all_jobs(companies, include_boards=True):
    all_jobs = []
    
    for company in companies:
        name = company.get('name')
        ats = company.get('ats')
        url = company.get('source_url')
        
        print(f"Scraping {name} via {ats}...")
        
        if ats == 'lever':
            jobs = scrape_lever(name, url)
            all_jobs.extend(jobs)
        elif ats == 'greenhouse':
            jobs = scrape_greenhouse(name, url)
            all_jobs.extend(jobs)
        elif ats == 'ashby':
            jobs = scrape_ashby(name, url)
            all_jobs.extend(jobs)
        else:
            print(f"Unsupported ATS '{ats}' for {name}")
            
    if include_boards:
        print("Scraping Remotive board...")
        all_jobs.extend(scrape_remotive())
        
    return all_jobs
