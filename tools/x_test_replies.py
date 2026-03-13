#!/usr/bin/env python3
"""
One-off X API v2 test: retrieve replies to a specific tweet.

Requirements:
- Input: tweet ID
- Use the X API search endpoint
- Query replies referencing the tweet
- Return username, user ID, and reply text
- Print results to console
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


def search_replies(tweet_id: str, bearer_token: str) -> Dict[str, Any]:
    """
    Use recent search to find replies in the same conversation as the tweet.

    Query strategy:
      - conversation_id:<tweet_id> is:reply
    """
    import urllib.request
    from urllib.parse import urlencode

    base_url = "https://api.x.com/2/tweets/search/recent"
    query = f"conversation_id:{tweet_id} is:reply"

    params = {
        "query": query,
        "max_results": "50",
        "tweet.fields": "author_id,created_at,conversation_id,in_reply_to_user_id",
        "expansions": "author_id",
        "user.fields": "id,username,name",
    }

    url = f"{base_url}?{urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "OpenClawXTestReplies/0.1",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body)


def extract_replies(payload: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """
    Return a list of (username, user_id, text) tuples for each reply tweet.
    """
    tweets: List[Dict[str, Any]] = payload.get("data") or []
    includes = payload.get("includes") or {}
    users: List[Dict[str, Any]] = includes.get("users") or []
    users_by_id: Dict[str, Dict[str, Any]] = {u.get("id", ""): u for u in users if u.get("id")}

    results: List[Tuple[str, str, str]] = []
    for t in tweets:
        author_id = t.get("author_id", "")
        user = users_by_id.get(author_id, {})
        username = user.get("username", "unknown")
        user_id = user.get("id", author_id)
        text = t.get("text", "").replace("\n", " ")
        results.append((username, user_id, text))

    return results


def main() -> None:
    load_env()

    if len(sys.argv) < 2:
        print("Usage: python3 tools/x_test_replies.py <tweet_id>", file=sys.stderr)
        sys.exit(1)

    tweet_id = sys.argv[1].strip()
    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        print("Error: X_BEARER_TOKEN is not set in the environment.", file=sys.stderr)
        sys.exit(1)

    try:
        print(f"Searching for replies to tweet {tweet_id}...", file=sys.stderr)
        payload = search_replies(tweet_id, bearer)
    except Exception as exc:
        print(f"Failure: exception during search — {exc}", file=sys.stderr)
        sys.exit(1)

    replies = extract_replies(payload)

    if not replies:
        print("No replies found for this tweet in recent search results.")
    else:
        print(f"Found {len(replies)} replies:\n")
        for username, user_id, text in replies:
            print(f"- @{username} (id={user_id}): {text}")

    # Optionally, print raw payload for debugging
    # print("\nRaw API response:")
    # print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

