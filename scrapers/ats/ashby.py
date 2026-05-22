import requests
from datetime import datetime

def scrape_ashby(company_name, source_url):
    board_token = source_url.rstrip('/').split('/')[-1]
    api_url = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
    
    headers = {
        "content-type": "application/json",
        "accept": "application/json"
    }
    
    payload = {
        "operationName": "ApiJobBoardWithTeams",
        "variables": {
            "organizationHostedJobsPageName": board_token
        },
        "query": "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) { jobPostings { id title locationName isRemote jobUrl publishedAt } } }"
    }
    
    jobs = []
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        postings = data.get('data', {}).get('jobBoard', {}).get('jobPostings', [])
        for job in postings:
            title = job.get('title', '')
            location = job.get('locationName', '')
            if job.get('isRemote'):
                location += " (Remote)"
            url = job.get('jobUrl', '')
            
            posted_at = 0
            published_at_str = job.get('publishedAt')
            if published_at_str:
                try:
                    posted_at = int(datetime.fromisoformat(published_at_str.replace('Z', '+00:00')).timestamp())
                except:
                    pass
            
            jobs.append({
                "title": title,
                "company": company_name,
                "location": location,
                "url": url,
                "description": "", # Ashby API might not return description in list
                "source": "ashby",
                "posted_at": posted_at
            })
    except Exception as e:
        print(f"Error scraping Ashby for {company_name}: {e}")
        
    return jobs
