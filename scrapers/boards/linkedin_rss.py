import feedparser
from urllib.parse import quote
import time

def scrape_linkedin_rss(keywords, location="Worldwide"):
    # This might have limited functionality as LinkedIn restricts RSS, but following requirements
    query = quote(f"{keywords}")
    loc = quote(location)
    url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={loc}&f_TPR=r86400&format=rss"
    
    jobs = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            # LinkedIn rss title format is typically: "Role at Company"
            title = entry.title
            company = ""
            if " at " in title:
                parts = title.split(" at ")
                title = parts[0]
                company = parts[1]
                
            posted_at = 0
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                posted_at = int(time.mktime(entry.published_parsed))
                
            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "url": entry.link,
                "description": entry.summary[:5000],
                "source": "linkedin_rss",
                "posted_at": posted_at
            })
    except Exception as e:
        print(f"Error scraping LinkedIn RSS: {e}")
        
    return jobs
