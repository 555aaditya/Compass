import requests
from datetime import datetime

def scrape_greenhouse(company_name, source_url):
    board_token = source_url.rstrip('/').split('/')[-1]
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    
    jobs = []
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for job in data.get('jobs', []):
            title = job.get('title', '')
            location = job.get('location', {}).get('name', '')
            url = job.get('absolute_url', '')
            description = job.get('content', '') # Requires decoding html if we want plain text, or we leave it.
            
            # Simple html tag stripping
            import re
            clean_description = re.sub('<[^<]+?>', '', description)
            
            posted_at = 0
            updated_at_str = job.get('updated_at')
            if updated_at_str:
                try:
                    posted_at = int(datetime.fromisoformat(updated_at_str.replace('Z', '+00:00')).timestamp())
                except:
                    pass
            
            jobs.append({
                "title": title,
                "company": company_name,
                "location": location,
                "url": url,
                "description": clean_description[:5000],
                "source": "greenhouse",
                "posted_at": posted_at
            })
    except Exception as e:
        print(f"Error scraping Greenhouse for {company_name}: {e}")
        
    return jobs
