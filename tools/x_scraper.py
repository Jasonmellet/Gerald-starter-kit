#!/usr/bin/env python3
"""
X (Twitter) scraper using Nitter/xCancel instances.
Fetches public tweet text without API access.

Usage:
  python3 tools/x_scraper.py tweet <tweet_url_or_id>
  python3 tools/x_scraper.py user <username>

Examples:
  python3 tools/x_scraper.py tweet https://x.com/matthewberman/status/2030423565355676100
  python3 tools/x_scraper.py tweet 2030423565355676100
  python3 tools/x_scraper.py user matthewberman
"""

import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError

# Nitter/xCancel instances that often work
INSTANCES = [
    "https://xcancel.com",
    "https://nitter.net",
    "https://nitter.it",
    "https://nitter.cz",
]


def fetch_url(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch URL content with basic headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "identity",
        "Connection": "keep-alive",
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except HTTPError as e:
        if e.code == 404:
            print(f"  404 - Not found", file=sys.stderr)
        elif e.code == 403:
            print(f"  403 - Blocked", file=sys.stderr)
        else:
            print(f"  HTTP {e.code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return None


def extract_tweet_from_html(html: str) -> Optional[dict]:
    """Extract tweet data from Nitter/xCancel HTML."""
    tweet = {}
    
    # Extract tweet text
    text_match = re.search(r'<div class="tweet-content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if text_match:
        text = text_match.group(1)
        # Clean up HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = ' '.join(text.split())  # Normalize whitespace
        tweet['text'] = text
    
    # Extract author
    author_match = re.search(r'<a class="username"[^>]*>(@[^<]+)</a>', html)
    if author_match:
        tweet['author'] = author_match.group(1)
    
    # Extract date
    date_match = re.search(r'<span[^>]*class="[^"]*tweet-date[^"]*"[^>]*title="([^"]+)"', html)
    if date_match:
        tweet['date'] = date_match.group(1)
    
    # Extract stats
    stats_match = re.search(r'<div class="tweet-stats">(.*?)</div>', html, re.DOTALL)
    if stats_match:
        stats_html = stats_match.group(1)
        likes = re.search(r'([\d,]+)\s*likes?', stats_html, re.IGNORECASE)
        retweets = re.search(r'([\d,]+)\s*retweets?', stats_html, re.IGNORECASE)
        replies = re.search(r'([\d,]+)\s*replies?', stats_html, re.IGNORECASE)
        tweet['likes'] = likes.group(1) if likes else '0'
        tweet['retweets'] = retweets.group(1) if retweets else '0'
        tweet['replies'] = replies.group(1) if replies else '0'
    
    return tweet if 'text' in tweet else None


def get_tweet(tweet_id: str, username: Optional[str] = None) -> Optional[dict]:
    """Fetch a tweet by ID using available instances."""
    # Try with username if provided
    if username:
        paths = [f"/{username}/status/{tweet_id}"]
    else:
        # Try common paths
        paths = [f"/i/status/{tweet_id}", f"/status/{tweet_id}"]
    
    for instance in INSTANCES:
        for path in paths:
            url = f"{instance}{path}"
            print(f"Trying {instance}...", file=sys.stderr)
            
            html = fetch_url(url)
            if html:
                tweet = extract_tweet_from_html(html)
                if tweet:
                    tweet['url'] = url
                    return tweet
    
    return None


def get_user_timeline(username: str, max_tweets: int = 5) -> list:
    """Fetch recent tweets from a user's timeline."""
    username = username.lstrip('@')
    tweets = []
    
    for instance in INSTANCES:
        url = f"{instance}/{username}"
        print(f"Trying {instance}...", file=sys.stderr)
        
        html = fetch_url(url)
        if html:
            # Extract multiple tweets from timeline
            tweet_divs = re.findall(r'<div class="timeline-item"[^>]*>(.*?)</div>\s*</div>\s*<div class="timeline-item"', html, re.DOTALL)
            
            for div in tweet_divs[:max_tweets]:
                tweet = extract_tweet_from_html(div)
                if tweet:
                    tweets.append(tweet)
            
            if tweets:
                return tweets
    
    return tweets


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "tweet":
        input_str = sys.argv[2]
        
        # Parse URL or ID
        if 'x.com' in input_str or 'twitter.com' in input_str:
            match = re.search(r'status/(\d+)', input_str)
            if match:
                tweet_id = match.group(1)
                username_match = re.search(r'x\.com/(\w+)/status', input_str)
                username = username_match.group(1) if username_match else None
            else:
                print("Error: Could not extract tweet ID from URL", file=sys.stderr)
                sys.exit(1)
        else:
            tweet_id = input_str
            username = None
        
        print(f"Fetching tweet {tweet_id}...")
        tweet = get_tweet(tweet_id, username)
        
        if tweet:
            print(f"\n{tweet.get('author', '@unknown')}")
            print(f"{tweet.get('text', '')}")
            print(f"\n📅 {tweet.get('date', 'Unknown')}")
            print(f"❤️ {tweet.get('likes', '0')}  🔁 {tweet.get('retweets', '0')}  💬 {tweet.get('replies', '0')}")
            print(f"\n🔗 {tweet.get('url', '')}")
        else:
            print("Error: Could not fetch tweet. All instances failed or returned no data.", file=sys.stderr)
            sys.exit(1)
    
    elif cmd == "user":
        username = sys.argv[2].lstrip('@')
        max_tweets = int(sys.argv[4]) if len(sys.argv) > 3 and sys.argv[3] == '--max' else 5
        
        print(f"Fetching timeline for @{username}...")
        tweets = get_user_timeline(username, max_tweets)
        
        if tweets:
            print(f"\nFound {len(tweets)} tweets:\n")
            for i, tweet in enumerate(tweets, 1):
                print(f"--- Tweet {i} ---")
                print(f"{tweet.get('text', '')[:200]}{'...' if len(tweet.get('text', '')) > 200 else ''}")
                print(f"📅 {tweet.get('date', 'Unknown')} | ❤️ {tweet.get('likes', '0')}\n")
        else:
            print("Error: Could not fetch timeline. All instances failed.", file=sys.stderr)
            sys.exit(1)
    
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
