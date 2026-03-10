#!/usr/bin/env python3
"""
X (Twitter) Monitor - Watch for new tweets from specific users

Usage:
  python3 tools/x_monitor.py --user matthewberman --interval 300
  python3 tools/x_monitor.py --user matthewberman --once

Options:
  --user      Username to monitor (required)
  --interval  Seconds between checks (default: 300 = 5 min)
  --once      Run once and exit (don't loop)
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode

# Load .env
def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ.setdefault(key, val)

load_env()

BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")
BASE_URL = "https://api.x.com/2"
STATE_FILE = Path(__file__).resolve().parent.parent / "memory" / "x_monitor_state.json"


def api_request(endpoint: str, params: dict = None) -> dict:
    """Make authenticated request to X API v2."""
    import urllib.request
    
    if not BEARER_TOKEN:
        print("Error: X_BEARER_TOKEN not found in .env", file=sys.stderr)
        sys.exit(1)
    
    url = f"{BASE_URL}{endpoint}"
    if params:
        url += "?" + urlencode(params)
    
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {BEARER_TOKEN}"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API Error {e.code}: {e.read().decode()}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return {}


def get_user_id(username: str) -> str:
    """Get user ID from username."""
    result = api_request(f"/users/by/username/{username.lstrip('@')}", {"user.fields": "id"})
    return result.get("data", {}).get("id") if result else None


def get_recent_tweets(user_id: str, since_id: str = None) -> list:
    """Get recent tweets from user."""
    params = {
        "max_results": 10,
        "tweet.fields": "created_at,public_metrics,source",
        "exclude": "replies,retweets"
    }
    if since_id:
        params["since_id"] = since_id
    
    result = api_request(f"/users/{user_id}/tweets", params)
    return result.get("data", []) if result else []


def load_state():
    """Load last seen tweet IDs."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state):
    """Save last seen tweet IDs."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def format_tweet(tweet: dict) -> str:
    """Format tweet for display."""
    text = tweet.get("text", "")
    created = tweet.get("created_at", "")
    metrics = tweet.get("public_metrics", {})
    
    lines = [
        f"{text}",
        f"",
        f"📅 {created[:10] if created else 'Unknown'} at {created[11:16] if created else 'Unknown'}",
        f"❤️ {metrics.get('like_count', 0)}  🔁 {metrics.get('retweet_count', 0)}  💬 {metrics.get('reply_count', 0)}",
        f"🔗 https://x.com/i/status/{tweet.get('id', '')}"
    ]
    return "\n".join(lines)


def monitor_user(username: str, interval: int = 300, once: bool = False):
    """Monitor a user for new tweets."""
    username = username.lstrip("@")
    print(f"🔍 Monitoring @{username} for new tweets...")
    print(f"⏱️  Check interval: {interval} seconds")
    print(f"💾 State file: {STATE_FILE}")
    print("-" * 50)
    
    # Get user ID
    user_id = get_user_id(username)
    if not user_id:
        print(f"❌ Could not find user @{username}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ Found user ID: {user_id}")
    
    # Load state
    state = load_state()
    last_seen_id = state.get(username)
    
    if last_seen_id:
        print(f"📌 Last seen tweet: {last_seen_id}")
    else:
        print("📌 No previous state — will show latest tweets on first run")
    
    print("-" * 50)
    
    while True:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for new tweets...")
        
        tweets = get_recent_tweets(user_id, last_seen_id)
        
        if tweets:
            # Filter to only new tweets (newer than last_seen_id)
            new_tweets = []
            for tweet in tweets:
                tweet_id = int(tweet.get("id", 0))
                if not last_seen_id or tweet_id > int(last_seen_id):
                    new_tweets.append(tweet)
            
            if new_tweets:
                print(f"\n🚨 {len(new_tweets)} NEW TWEET(S) from @{username}!\n")
                for tweet in reversed(new_tweets):  # Oldest first
                    print("=" * 50)
                    print(format_tweet(tweet))
                    print("=" * 50)
                    print()
                
                # Update state with newest tweet ID
                newest_id = max(int(t.get("id", 0)) for t in new_tweets)
                state[username] = str(newest_id)
                save_state(state)
                last_seen_id = str(newest_id)
            else:
                print("✓ No new tweets")
        else:
            print("✓ No tweets found")
        
        if once:
            print("\n👋 --once flag set, exiting.")
            break
        
        print(f"💤 Sleeping {interval} seconds...")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Monitor X/Twitter users for new tweets")
    parser.add_argument("--user", required=True, help="Username to monitor (without @)")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between checks (default: 300)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    try:
        monitor_user(args.user, args.interval, args.once)
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
