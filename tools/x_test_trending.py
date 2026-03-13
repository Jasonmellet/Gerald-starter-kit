#!/usr/bin/env python3
"""
One-off X API v2 test: approximate "trending" posts for a topic.

Behavior:
- Input: search query (e.g. "ai agents", "cold email").
- Uses GET /2/tweets/search/recent with X_BEARER_TOKEN.
- Sorts results by total engagement (likes + replies + retweets + quotes).
- Prints the top N posts with author, text, and metrics.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_env() -> None:
    """Load .env from workspace root if present."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ.setdefault(key, val)


def search_recent(query: str, bearer_token: str, max_results: int = 50) -> Dict[str, Any]:
    """Call /2/tweets/search/recent."""
    import urllib.request
    from urllib.parse import urlencode

    base_url = "https://api.x.com/2/tweets/search/recent"
    params = {
        "query": query,
        "max_results": str(min(max_results, 100)),
        "tweet.fields": "created_at,author_id,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,verified",
    }

    url = f"{base_url}?{urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "OpenClawXTestTrending/0.1",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body)


def score_tweet(tweet: Dict[str, Any]) -> int:
    """Simple engagement score = likes + replies + retweets + quotes."""
    m = tweet.get("public_metrics") or {}
    return int(m.get("like_count", 0)) + int(m.get("reply_count", 0)) + int(
        m.get("retweet_count", 0)
    ) + int(m.get("quote_count", 0))


def main() -> None:
    load_env()

    if len(sys.argv) < 2:
        print(
            "Usage: python3 tools/x_test_trending.py \"search query\" [topN]",
            file=sys.stderr,
        )
        sys.exit(1)

    query = sys.argv[1]
    top_n = 10
    if len(sys.argv) >= 3:
        try:
            top_n = max(1, int(sys.argv[2]))
        except ValueError:
            pass

    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        print("Error: X_BEARER_TOKEN is not set in the environment.", file=sys.stderr)
        sys.exit(1)

    print(f"Searching recent tweets for query: {query!r}")
    try:
        payload = search_recent(query, bearer, max_results=50)
    except Exception as exc:
        print(f"Failure: exception during search — {exc}", file=sys.stderr)
        sys.exit(1)

    tweets: List[Dict[str, Any]] = payload.get("data") or []
    includes = payload.get("includes") or {}
    users = {u.get("id"): u for u in includes.get("users", []) if u.get("id")}

    if not tweets:
        print("No tweets returned for this query.")
        sys.exit(0)

    # Sort by engagement score descending
    scored: List[Tuple[int, Dict[str, Any]]] = [(score_tweet(t), t) for t in tweets]
    scored.sort(key=lambda x: x[0], reverse=True)

    print(f"\nTop {min(top_n, len(scored))} posts by engagement:\n")
    for rank, (score, tweet) in enumerate(scored[:top_n], start=1):
        author_id = tweet.get("author_id")
        user = users.get(author_id, {})
        username = user.get("username", "unknown")
        metrics = tweet.get("public_metrics", {})
        text = tweet.get("text", "").replace("\n", " ")
        created_at = tweet.get("created_at", "")
        print(f"{rank}. @{username} — score={score}")
        print(f"   id={tweet.get('id')} created_at={created_at}")
        print(
            f"   likes={metrics.get('like_count',0)} replies={metrics.get('reply_count',0)} "
            f"retweets={metrics.get('retweet_count',0)} quotes={metrics.get('quote_count',0)}"
        )
        print(f"   text={text}")
        print()


if __name__ == "__main__":
    main()

