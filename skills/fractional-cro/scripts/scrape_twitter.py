#!/usr/bin/env python3
"""
Scrape Twitter/X for lead opportunities.
Uses Nitter instances (Twitter frontend) to avoid API limits.
"""

import requests
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

DB_PATH = Path(__file__).parent.parent / 'data' / 'leads.db'

# Search queries for finding leads
SEARCH_QUERIES = [
    '"looking for a CMO"',
    '"fractional CMO"',
    '"first marketing hire"',
    '"need marketing help"',
    '"AI automation" startup',
    '"building an AI agent"',
    '"growth marketing" hiring'
]

def search_twitter(query):
    """Search Twitter via Nitter."""
    # Nitter instances often change/block — this is a best-effort approach
    nitter_hosts = [
        'https://nitter.net',
        'https://nitter.it',
        'https://nitter.cz'
    ]
    
    encoded_query = quote(query)
    
    for host in nitter_hosts:
        try:
            url = f"{host}/search?f=tweets&q={encoded_query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return parse_nitter_results(response.text, query)
        except Exception as e:
            continue
    
    return []

def parse_nitter_results(html, query):
    """Parse Nitter HTML for tweets."""
    from html.parser import HTMLParser
    
    leads = []
    
    # Simple regex extraction (Nitter uses specific class names)
    tweet_pattern = r'<div class="tweet-content[^"]*">.*?<div class="tweet-body">.*?<a href="([^"]*)">.*?<div class="tweet-content media-body">.*?<div class="content">(.*?)</div>.*?</div>'
    
    matches = re.findall(tweet_pattern, html, re.DOTALL)
    
    for url_path, content_html in matches[:10]:  # Limit to 10
        # Clean HTML tags
        text = re.sub(r'<[^>]+>', '', content_html)
        text = text.replace('&quot;', '"').replace('&amp;', '&')
        
        # Extract username
        username_match = re.search(r'/([^/]+)/status/', url_path)
        username = username_match.group(1) if username_match else 'unknown'
        
        leads.append({
            'username': username,
            'text': text[:500],
            'url': f"https://twitter.com{url_path}",
            'query': query
        })
    
    return leads

def save_lead(source_id, username, url, description, tags):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO leads 
            (source, source_id, contact_name, url, description, tags, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('twitter', source_id, username, url, description, tags, datetime.now()))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving lead: {e}")
        return False
    finally:
        conn.close()

def scrape_twitter():
    print("Searching Twitter for leads...")
    total_new = 0
    
    for query in SEARCH_QUERIES:
        print(f"\nQuery: {query}")
        tweets = search_twitter(query)
        
        for tweet in tweets:
            source_id = f"{tweet['username']}_{hash(tweet['url']) % 10000000}"
            
            if save_lead(
                source_id,
                tweet['username'],
                tweet['url'],
                tweet['text'],
                query
            ):
                total_new += 1
                print(f"  New: @{tweet['username']}: {tweet['text'][:60]}...")
    
    print(f"\nTotal new leads from Twitter: {total_new}")
    return total_new

if __name__ == '__main__':
    scrape_twitter()
