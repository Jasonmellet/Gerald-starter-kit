#!/usr/bin/env python3
"""
X (Twitter) Multi-User Monitor - Watch for new tweets from specific users

Monitors: matthewberman, neilpatel, dataforseo, steipete

Usage:
  python3 tools/x_multi_monitor.py --interval 300
  python3 tools/x_multi_monitor.py --once
  python3 tools/x_multi_monitor.py --list-users

Options:
  --interval    Seconds between checks (default: 300 = 5 min)
  --once        Run once and exit
  --list-users  Show monitored users and exit
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
STATE_FILE = Path(__file__).resolve().parent.parent / "memory" / "x_multi_monitor_state.json"

# Monitored users with descriptions
MONITORED_USERS = {
    "matthewberman": "OpenClaw, AI agents, security frameworks",
    "neilpatel": "Marketing, SEO, business growth strategies",
    "dataforseo": "SEO data, API updates, research tools",
    "steipete": "Peter Steinberger - OpenClaw creator",
    "gregisenberg": "Tech updates, tips and tricks"
}


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


def format_tweet(tweet: dict, username: str) -> str:
    """Format tweet for display."""
    text = tweet.get("text", "")
    created = tweet.get("created_at", "")
    metrics = tweet.get("public_metrics", {})
    
    lines = [
        f"🐦 @{username}",
        f"",
        f"{text}",
        f"",
        f"📅 {created[:10] if created else 'Unknown'} at {created[11:16] if created else 'Unknown'}",
        f"❤️ {metrics.get('like_count', 0)}  🔁 {metrics.get('retweet_count', 0)}  💬 {metrics.get('reply_count', 0)}",
        f"🔗 https://x.com/i/status/{tweet.get('id', '')}"
    ]
    return "\n".join(lines)


def check_user(username: str, user_id: str, state: dict) -> tuple:
    """Check a single user for new tweets. Returns (new_tweets, updated_state)."""
    last_seen_id = state.get(username)
    tweets = get_recent_tweets(user_id, last_seen_id)
    
    if not tweets:
        return [], state
    
    # Filter to only new tweets
    new_tweets = []
    for tweet in tweets:
        tweet_id = int(tweet.get("id", 0))
        if not last_seen_id or tweet_id > int(last_seen_id):
            new_tweets.append(tweet)
    
    if new_tweets:
        # Update state with newest tweet ID
        newest_id = max(int(t.get("id", 0)) for t in tweets)
        state[username] = str(newest_id)
    
    return new_tweets, state


def monitor_all(interval: int = 300, once: bool = False):
    """Monitor all configured users."""
    print("🔍 X Multi-User Monitor")
    print("=" * 50)
    print("\nMonitored accounts:")
    for username, description in MONITORED_USERS.items():
        print(f"  @{username} — {description}")
    print(f"\n⏱️  Check interval: {interval} seconds")
    print(f"💾 State file: {STATE_FILE}")
    print("=" * 50)
    
    # Resolve user IDs
    print("\nResolving user IDs...")
    user_ids = {}
    for username in MONITORED_USERS:
        user_id = get_user_id(username)
        if user_id:
            user_ids[username] = user_id
            print(f"  ✅ @{username}: {user_id}")
        else:
            print(f"  ❌ @{username}: Could not resolve")
    
    if not user_ids:
        print("\n❌ No users could be resolved. Exiting.", file=sys.stderr)
        sys.exit(1)
    
    # Load state
    state = load_state()
    print(f"\n💾 Loaded state for {len(state)} users")
    
    print("\n" + "=" * 50)
    
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{timestamp}] Checking {len(user_ids)} users...")
        print("-" * 50)
        
        total_new = 0
        for username, user_id in user_ids.items():
            new_tweets, state = check_user(username, user_id, state)
            
            if new_tweets:
                total_new += len(new_tweets)
                print(f"\n🚨 @{username}: {len(new_tweets)} NEW TWEET(S)!\n")
                for tweet in reversed(new_tweets):  # Oldest first
                    print("=" * 50)
                    print(format_tweet(tweet, username))
                    print("=" * 50)
                    print()
            else:
                print(f"  ✓ @{username}: No new tweets")
        
        if total_new > 0:
            save_state(state)
            print(f"\n💾 Saved state ({total_new} new tweets total)")
        
        if once:
            print("\n👋 --once flag set, exiting.")
            break
        
        print(f"\n💤 Sleeping {interval} seconds...")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Monitor multiple X/Twitter users for new tweets")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between checks (default: 300)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--list-users", action="store_true", help="Show monitored users and exit")
    
    args = parser.parse_args()
    
    if args.list_users:
        print("Monitored accounts:")
        for username, description in MONITORED_USERS.items():
            print(f"  @{username} — {description}")
        sys.exit(0)
    
    try:
        monitor_all(args.interval, args.once)
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
