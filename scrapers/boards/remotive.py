import requests
from datetime import datetime

def scrape_remotive():
    # unlimited free api for remote jobs
    url = "https://remotive.com/api/remote-jobs?category=software-dev"
    
    jobs = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for job in data.get('jobs', [])[:100]: # Limit to recent 100 for speed
            title = job.get('title', '')
            company = job.get('company_name', '')
            location = job.get('candidate_required_location', 'Remote')
            job_url = job.get('url', '')
            description = job.get('description', '')
            
            import re
            clean_description = re.sub('<[^<]+?>', '', description)
            
            posted_at = 0
            pub_date_str = job.get('publication_date')
            if pub_date_str:
                try:
                    posted_at = int(datetime.fromisoformat(pub_date_str.replace('Z', '+00:00')).timestamp())
                except:
                    pass
            
            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "description": clean_description[:5000],
                "source": "remotive",
                "posted_at": posted_at
            })
    except Exception as e:
        print(f"Error scraping Remotive: {e}")
        
    return jobs
