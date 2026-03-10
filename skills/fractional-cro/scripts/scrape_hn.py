#!/usr/bin/env python3
"""
Scrape Hacker News "Who's Hiring" threads.
"""

import requests
import sqlite3
import re
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / 'data' / 'leads.db'
HN_API = 'https://hacker-news.firebaseio.com/v0'

def get_item(item_id):
    """Fetch a single item from HN API."""
    try:
        response = requests.get(f"{HN_API}/item/{item_id}.json", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching item {item_id}: {e}")
        return None

def get_who_is_hiring_stories():
    """Find recent 'Who is hiring?' stories."""
    try:
        response = requests.get(f"{HN_API}/topstories.json", timeout=30)
        response.raise_for_status()
        top_stories = response.json()[:100]
        
        hiring_stories = []
        for story_id in top_stories:
            story = get_item(story_id)
            if story and story.get('title'):
                title_lower = story['title'].lower()
                if 'who is hiring' in title_lower or 'who wants to be hired' in title_lower:
                    hiring_stories.append(story)
        
        return hiring_stories
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return []

def parse_job_comment(comment):
    """Extract job details from a comment."""
    text = comment.get('text', '')
    
    # Look for marketing/growth/AI roles
    keywords = [
        'marketing', 'growth', 'cmo', 'head of marketing',
        'ai engineer', 'ml engineer', 'automation',
        'fractional', 'consultant', 'advisor'
    ]
    
    text_lower = text.lower()
    if not any(kw in text_lower for kw in keywords):
        return None
    
    # Extract company name (usually first line or before |)
    lines = text.split('\n')
    company = lines[0].split('|')[0].strip() if lines else 'Unknown'
    
    return {
        'company': company[:100],
        'description': text[:1000],
        'url': f"https://news.ycombinator.com/item?id={comment['id']}"
    }

def save_lead(source_id, company, title, url, description):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO leads 
            (source, source_id, company, title, url, description, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('hackernews', source_id, company, title, url, description, datetime.now()))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving lead: {e}")
        return False
    finally:
        conn.close()

def scrape_hn():
    print("Fetching HN 'Who is Hiring' threads...")
    hiring_stories = get_who_is_hiring_stories()
    
    if not hiring_stories:
        print("No hiring threads found in top stories")
        return 0
    
    total_new = 0
    
    for story in hiring_stories[:2]:  # Check top 2 hiring threads
        print(f"\nScanning: {story['title']}")
        
        # Get top-level comments (job postings)
        kids = story.get('kids', [])
        
        for comment_id in kids[:100]:  # Limit to first 100 comments
            comment = get_item(comment_id)
            if not comment or comment.get('deleted') or not comment.get('text'):
                continue
            
            job = parse_job_comment(comment)
            if job:
                if save_lead(
                    str(comment_id),
                    job['company'],
                    'Job Posting',
                    job['url'],
                    job['description']
                ):
                    total_new += 1
                    print(f"  New: {job['company'][:50]}...")
    
    print(f"\nTotal new leads from HN: {total_new}")
    return total_new

if __name__ == '__main__':
    scrape_hn()
