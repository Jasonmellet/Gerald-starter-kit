#!/usr/bin/env python3
"""
Scrape Reddit for hiring posts and opportunities.
Uses Reddit JSON API (no auth required for read-only).
"""

import requests
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

DB_PATH = Path(__file__).parent.parent / 'data' / 'leads.db'

# Subreddits to monitor
SUBREDDITS = [
    'startups',
    'forhire',
    'jobbit',
    'marketing',
    'saas',
    'artificial',
    'MachineLearning'
]

# Keywords to filter posts
KEYWORDS = [
    'hiring',
    'looking for',
    'need a',
    'seeking',
    'fractional',
    'cmo',
    'marketing',
    'growth',
    'ai automation',
    'consultant'
]

def fetch_subreddit(subreddit, limit=50):
    """Fetch recent posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()['data']['children']
    except Exception as e:
        print(f"Error fetching r/{subreddit}: {e}")
        return []

def is_hiring_post(post):
    """Check if post is a hiring opportunity."""
    title = post['title'].lower()
    text = post.get('selftext', '').lower()
    combined = f"{title} {text}"
    
    # Must have at least one hiring keyword
    has_hiring_keyword = any(kw in combined for kw in KEYWORDS)
    
    # Exclude common non-opportunity posts
    excluded = [
        'i got hired',
        'just hired',
        'was hired',
        'got a job',
        'hired!',
        'promotion',
        'salary negotiation',
        'interview tips'
    ]
    
    is_excluded = any(excl in combined for excl in excluded)
    
    return has_hiring_keyword and not is_excluded

def extract_company(text):
    """Try to extract company name from post."""
    # Look for "at CompanyName" or "CompanyName is hiring"
    patterns = [
        r'at\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\s+(?:is\s+)?(?:hiring|looking)',
        r'([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\s+(?:is\s+)?(?:hiring|looking\s+for)',
        r'company:\s*([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None

def save_lead(source_id, subreddit, title, url, description, company=None):
    """Save lead to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO leads 
            (source, source_id, company, title, url, description, tags, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f'reddit-r/{subreddit}',
            source_id,
            company,
            title,
            url,
            description[:1000],
            subreddit,
            datetime.now()
        ))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving lead: {e}")
        return False
    finally:
        conn.close()

def scrape_reddit():
    """Scrape all configured subreddits."""
    total_new = 0
    
    for subreddit in SUBREDDITS:
        print(f"\nScraping r/{subreddit}...")
        posts = fetch_subreddit(subreddit)
        
        new_in_subreddit = 0
        for post_data in posts:
            post = post_data['data']
            
            if not is_hiring_post(post):
                continue
            
            post_id = post['id']
            title = post['title']
            url = urljoin('https://reddit.com', post['permalink'])
            text = post.get('selftext', '')
            company = extract_company(title + ' ' + text)
            
            if save_lead(post_id, subreddit, title, url, text, company):
                total_new += 1
                new_in_subreddit += 1
                company_str = f" [{company}]" if company else ""
                print(f"  New:{company_str} {title[:70]}...")
        
        if new_in_subreddit == 0:
            print(f"  No new leads")
    
    print(f"\n✅ Total new leads from Reddit: {total_new}")
    return total_new

if __name__ == '__main__':
    scrape_reddit()
