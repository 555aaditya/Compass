import requests

def scrape_lever(company_name, source_url):
    board_token = source_url.rstrip('/').split('/')[-1]
    api_url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
    
    jobs = []
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for job in data:
            title = job.get('text', '')
            location = job.get('categories', {}).get('location', '')
            url = job.get('hostedUrl', '')
            description = job.get('descriptionPlain', '') or job.get('description', '')
            
            # Additional location info
            workplace_type = job.get('workplaceType', '')
            if workplace_type:
                location = f"{location} ({workplace_type})"
                
            posted_at = job.get('createdAt')
            if posted_at:
                posted_at = int(posted_at / 1000) # Convert ms to seconds
            else:
                posted_at = 0
                
            jobs.append({
                "title": title,
                "company": company_name,
                "location": location,
                "url": url,
                "description": description[:5000],  # Limit size
                "source": "lever",
                "posted_at": posted_at
            })
    except Exception as e:
        print(f"Error scraping Lever for {company_name}: {e}")
        
    return jobs
