#!/usr/bin/env python3
"""
X (Twitter) API v2 client - Free Tier Compatible
Fetches tweets using only Free tier endpoints.

Free tier limits (as of 2024):
- Tweet lookup: 100 requests per 15 min (1,500/month)
- User lookup: 100 requests per 15 min (1,500/month) 
- No search, no timelines, no streaming

Usage:
  python3 tools/x_api_client_free.py tweet <tweet_id>
  python3 tools/x_api_client_free.py user <username>
  python3 tools/x_api_client_free.py limits
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional
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
BASE_URL = "https://api.twitter.com/2"


def api_request(endpoint: str, params: Optional[dict] = None) -> dict:
    """Make authenticated request to X API v2."""
    import urllib.request
    
    if not BEARER_TOKEN:
        print("Error: X_BEARER_TOKEN not found in .env", file=sys.stderr)
        sys.exit(1)
    
    url = f"{BASE_URL}{endpoint}"
    if params:
        url += "?" + urlencode(params)
    
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {BEARER_TOKEN}"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # Print rate limit info
            remaining = resp.headers.get('x-rate-limit-remaining')
            limit = resp.headers.get('x-rate-limit-limit')
            reset = resp.headers.get('x-rate-limit-reset')
            if remaining and limit:
                print(f"Rate limit: {remaining}/{limit} remaining", file=sys.stderr)
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        error_data = json.loads(err_body) if err_body else {}
        
        # Check for specific errors
        if e.code == 403:
            if "client-not-enrolled" in err_body:
                print("Error: This endpoint requires a paid subscription (Basic/Pro).", file=sys.stderr)
                print("Free tier has limited endpoint access.", file=sys.stderr)
            else:
                print(f"Error 403: {error_data.get('detail', 'Forbidden')}", file=sys.stderr)
        elif e.code == 429:
            print("Error 429: Rate limit exceeded. Wait 15 minutes.", file=sys.stderr)
        else:
            print(f"API Error {e.code}: {err_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)


def get_tweet(tweet_id: str) -> dict:
    """Fetch a single tweet by ID (Free tier: 100 req/15min)."""
    params = {
        "tweet.fields": "created_at,author_id,public_metrics,source",
        "expansions": "author_id",
        "user.fields": "username,public_metrics"
    }
    return api_request(f"/tweets/{tweet_id}", params)


def get_user_by_username(username: str) -> dict:
    """Fetch user info by username (Free tier: 100 req/15min)."""
    username = username.lstrip("@")
    params = {"user.fields": "created_at,public_metrics,description"}
    return api_request(f"/users/by/username/{username}", params)


def format_tweet(tweet: dict, users: Optional[dict] = None) -> str:
    """Pretty print a tweet."""
    text = tweet.get("text", "")
    created = tweet.get("created_at", "")
    metrics = tweet.get("public_metrics", {})
    
    author = "Unknown"
    if users and "author_id" in tweet:
        for u in users.get("users", []):
            if u["id"] == tweet["author_id"]:
                author = f"@{u['username']}"
                break
    
    output = []
    if author != "Unknown":
        output.append(f"@{author}")
    output.append(f"{text}")
    output.append(f"\n📅 {created[:10] if created else 'Unknown'}")
    output.append(f"❤️ {metrics.get('like_count', 0)}  🔁 {metrics.get('retweet_count', 0)}  💬 {metrics.get('reply_count', 0)}")
    
    return "\n".join(filter(None, output))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "tweet" and len(sys.argv) >= 3:
        tweet_id = sys.argv[2]
        print(f"Fetching tweet {tweet_id}...")
        result = get_tweet(tweet_id)
        
        if "data" in result:
            users = {u["id"]: u for u in result.get("includes", {}).get("users", [])}
            print("\n" + format_tweet(result["data"], {"users": list(users.values())}))
        else:
            print(json.dumps(result, indent=2))
    
    elif cmd == "user" and len(sys.argv) >= 3:
        username = sys.argv[2]
        print(f"Fetching user @{username.lstrip('@')}...")
        result = get_user_by_username(username)
        
        if "data" in result:
            u = result["data"]
            metrics = u.get("public_metrics", {})
            print(f"\n@{u['username']}")
            print(f"Name: {u.get('name', 'N/A')}")
            print(f"Created: {u.get('created_at', 'N/A')[:10]}")
            print(f"Followers: {metrics.get('followers_count', 0):,}")
            print(f"Following: {metrics.get('following_count', 0):,}")
            print(f"Tweets: {metrics.get('tweet_count', 0):,}")
            if u.get("description"):
                print(f"\nBio: {u['description']}")
        else:
            print(json.dumps(result, indent=2))
    
    elif cmd == "limits":
        print("Free Tier Limits:")
        print("  - Tweet lookup: 100 req/15 min (1,500/month)")
        print("  - User lookup: 100 req/15 min (1,500/month)")
        print("  - Search: NOT AVAILABLE (requires Basic+)")
        print("  - Timelines: NOT AVAILABLE (requires Basic+)")
        print("\nAvailable endpoints:")
        print("  - GET /tweets/:id (single tweet)")
        print("  - GET /users/by/username/:username (user info)")
    
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
