import os
import json
import time
from config_loader import CONFIG

def hard_filter(job):
    title = job.get('title', '').lower()
    
    # 1. Check title includes
    titles = [t.lower() for t in CONFIG['roles']['titles']]
    include_keywords = [k.lower() for t in CONFIG['roles']['include_keywords'] for k in (t,)]
    
    has_title_match = any(t in title for t in titles)
    has_include_match = any(k in title for k in include_keywords)
    
    if not (has_title_match or has_include_match):
        return False
        
    # 2. Check title excludes
    exclude_keywords = [k.lower() for k in CONFIG['roles']['exclude_keywords']]
    if any(k in title for k in exclude_keywords):
        return False
        
    # 3. Check Location
    # We will do a basic string match for locations
    location = job.get('location', '').lower()
    
    valid_location = False
    
    if CONFIG['locations']['remote'] and 'remote' in location:
        valid_location = True
        
    if CONFIG['locations']['india']['enabled']:
        cities = [c.lower() for c in CONFIG['locations']['india']['cities']]
        if any(c in location for c in cities) or 'india' in location:
            valid_location = True
            
    if CONFIG['locations']['international']['enabled']:
        countries = [c.lower() for c in CONFIG['locations']['international']['countries']]
        if any(c in location for c in countries):
            valid_location = True
            
    # For unspecified, we pass if the config says include
    if not valid_location and CONFIG['locations']['unspecified_location'] == 'include':
        valid_location = True
        
    if not valid_location:
        return False
        
    # 4. Check Date (must be within last 30 days)
    posted_at = job.get('posted_at', 0)
    if posted_at:
        current_time = int(time.time())
        # 30 days = 30 * 24 * 60 * 60 = 2592000 seconds
        if current_time - posted_at > 2592000:
            return False
            
    return True


def score_job(job):
    # Dummy scoring since agentic work is disabled
    return {"score": 10, "reason": "Passed hard filters", "flag": "strong_match"}

def process_jobs(jobs):
    min_score = CONFIG['alerts']['min_score']
    filtered = []
    
    for job in jobs:
        if hard_filter(job):
            scoring_result = score_job(job)
            if scoring_result.get('score', 0) >= min_score:
                job['score'] = scoring_result.get('score')
                job['reason'] = scoring_result.get('reason')
                filtered.append(job)
                
    return filtered
