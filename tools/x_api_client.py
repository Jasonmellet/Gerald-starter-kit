#!/usr/bin/env python3
"""
X (Twitter) API v2 client - PAYG Tier
Fetches tweets, user data, and more using X API v2.

Usage:
  python3 tools/x_api_client.py tweet <tweet_id>
  python3 tools/x_api_client.py user <username>
  python3 tools/x_api_client.py timeline <username> [--max 10]
  python3 tools/x_api_client.py search <query> [--max 10]
  python3 tools/x_api_client.py limits

Examples:
  python3 tools/x_api_client.py tweet 2030423565355676100
  python3 tools/x_api_client.py user matthewberman
  python3 tools/x_api_client.py timeline matthewberman --max 5
  python3 tools/x_api_client.py search "OpenClaw AI"
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
BASE_URL = "https://api.x.com/2"


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
            if remaining and limit:
                print(f"Rate limit: {remaining}/{limit} remaining", file=sys.stderr)
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        error_data = json.loads(err_body) if err_body else {}
        
        if e.code == 403:
            print(f"Error 403: {error_data.get('detail', 'Forbidden')}", file=sys.stderr)
            if "client-not-enrolled" in err_body:
                print("Your app may need to be recreated in the developer portal.", file=sys.stderr)
        elif e.code == 429:
            print("Error 429: Rate limit exceeded. Wait 15 minutes.", file=sys.stderr)
        else:
            print(f"API Error {e.code}: {err_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)


def get_tweet(tweet_id: str) -> dict:
    """Fetch a single tweet by ID."""
    params = {
        "tweet.fields": "created_at,author_id,public_metrics,source,entities",
        "expansions": "author_id",
        "user.fields": "username,public_metrics,verified"
    }
    return api_request(f"/tweets/{tweet_id}", params)


def get_user_by_username(username: str) -> dict:
    """Fetch user info by username."""
    username = username.lstrip("@")
    params = {"user.fields": "created_at,public_metrics,verified,description"}
    return api_request(f"/users/by/username/{username}", params)


def get_user_timeline(username: str, max_results: int = 10) -> dict:
    """Fetch recent tweets from a user's timeline."""
    user = get_user_by_username(username)
    user_id = user["data"]["id"]
    
    params = {
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,public_metrics",
        "exclude": "replies,retweets"
    }
    return api_request(f"/users/{user_id}/tweets", params)


def search_recent(query: str, max_results: int = 10) -> dict:
    """Search recent tweets (last 7 days)."""
    params = {
        "query": query,
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,author_id,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,verified"
    }
    return api_request("/tweets/search/recent", params)


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
            print(f"Verified: {u.get('verified', False)}")
            print(f"Created: {u.get('created_at', 'N/A')[:10]}")
            print(f"Followers: {metrics.get('followers_count', 0):,}")
            print(f"Following: {metrics.get('following_count', 0):,}")
            print(f"Tweets: {metrics.get('tweet_count', 0):,}")
            if u.get("description"):
                print(f"\nBio: {u['description']}")
        else:
            print(json.dumps(result, indent=2))
    
    elif cmd == "timeline" and len(sys.argv) >= 3:
        username = sys.argv[2]
        max_results = 10
        if "--max" in sys.argv:
            idx = sys.argv.index("--max")
            if idx + 1 < len(sys.argv):
                max_results = int(sys.argv[idx + 1])
        
        print(f"Fetching timeline for @{username.lstrip('@')}...")
        result = get_user_timeline(username, max_results)
        
        if "data" in result:
            print(f"\nFound {len(result['data'])} tweets:\n")
            for tweet in result["data"]:
                print(format_tweet(tweet))
                print("-" * 50)
        else:
            print(json.dumps(result, indent=2))
    
    elif cmd == "search" and len(sys.argv) >= 3:
        query = sys.argv[2]
        max_results = 10
        if "--max" in sys.argv:
            idx = sys.argv.index("--max")
            if idx + 1 < len(sys.argv):
                max_results = int(sys.argv[idx + 1])
        
        print(f"Searching for '{query}'...")
        result = search_recent(query, max_results)
        
        if "data" in result:
            users = {u["id"]: u for u in result.get("includes", {}).get("users", [])}
            print(f"\nFound {len(result['data'])} tweets:\n")
            for tweet in result["data"]:
                print(format_tweet(tweet, {"users": list(users.values())}))
                print("-" * 50)
        else:
            print(json.dumps(result, indent=2))
    
    elif cmd == "limits":
        print("PAYG Tier Limits (varies by endpoint):")
        print("  - Tweet lookup: Check x-rate-limit headers")
        print("  - User lookup: Check x-rate-limit headers")
        print("  - Search recent: 450 req/15 min")
        print("  - User timeline: 1500 req/15 min")
        print("\nAvailable endpoints:")
        print("  - GET /tweets/:id")
        print("  - GET /users/by/username/:username")
        print("  - GET /users/:id/tweets")
        print("  - GET /tweets/search/recent")
    
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
