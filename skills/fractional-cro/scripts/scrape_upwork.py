#!/usr/bin/env python3
"""
Scrape Upwork job postings for relevant opportunities.
"""

import requests
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / 'data' / 'leads.db'
CONFIG_PATH = Path(__file__).parent.parent / 'config.json'

# Upwork RSS feeds for categories
UPWORK_RSS_URLS = {
    'marketing': 'https://www.upwork.com/ab/feed/jobs/rss?q=marketing&sort=recency',
    'ai-ml': 'https://www.upwork.com/ab/feed/jobs/rss?q=artificial%20intelligence&sort=recency',
    'automation': 'https://www.upwork.com/ab/feed/jobs/rss?q=automation&sort=recency',
    'cmo': 'https://www.upwork.com/ab/feed/jobs/rss?q=fractional%20cmo&sort=recency'
}

def parse_rss_feed(url):
    """Parse RSS feed and return job entries."""
    try:
        import xml.etree.ElementTree as ET
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        # Handle RSS namespace
        ns = {'rss': 'http://purl.org/rss/1.0/'}
        
        items = []
        for item in root.findall('.//item'):
            title = item.find('title')
            link = item.find('link')
            desc = item.find('description')
            pub_date = item.find('pubDate')
            
            items.append({
                'title': title.text if title is not None else '',
                'url': link.text if link is not None else '',
                'description': desc.text if desc is not None else '',
                'published': pub_date.text if pub_date is not None else ''
            })
        
        return items
    except Exception as e:
        print(f"Error parsing feed {url}: {e}")
        return []

def save_lead(source_id, title, url, description):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO leads 
            (source, source_id, company, title, url, description, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('upwork', source_id, None, title, url, description, datetime.now()))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving lead: {e}")
        return False
    finally:
        conn.close()

def scrape_upwork():
    total_new = 0
    
    for category, url in UPWORK_RSS_URLS.items():
        print(f"Scraping Upwork: {category}")
        jobs = parse_rss_feed(url)
        
        for job in jobs:
            # Create unique ID from URL
            source_id = job['url'].split('~')[-1].split('/')[0] if '~' in job['url'] else job['url'][-20:]
            
            if save_lead(source_id, job['title'], job['url'], job['description']):
                total_new += 1
                print(f"  New: {job['title'][:60]}...")
    
    print(f"\nTotal new leads from Upwork: {total_new}")
    return total_new

if __name__ == '__main__':
    scrape_upwork()
