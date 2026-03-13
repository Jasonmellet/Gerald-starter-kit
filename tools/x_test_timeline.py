#!/usr/bin/env python3
"""
One-off X API v2 test: fetch the 10 most recent posts for this account.

Requirements:
- Use GET /2/users/:id/tweets
- Return tweet ID, text, and timestamp
- Print results to console
- Confirm the known test post appears in the results (if present)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


MAX_RESULTS = 10
# From earlier test run; used only for presence check, script still works without it.
KNOWN_TEST_TWEET_ID = "2032530013572985142"


def load_env() -> None:
    """Load .env from workspace root if present."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ.setdefault(key, val)


def get_user_id_from_access_token() -> Optional[str]:
    """
    Extract the numeric user ID from X_ACCESS_TOKEN.

    OAuth 1.0a access tokens have the form "<user_id>-<random_string>".
    """
    token = os.environ.get("X_ACCESS_TOKEN") or os.environ.get("x_access_token")
    if not token:
        return None
    user_id = token.split("-", 1)[0]
    return user_id if user_id.isdigit() else None


def fetch_recent_tweets(user_id: str, bearer_token: str) -> Dict[str, Any]:
    """Call GET /2/users/:id/tweets."""
    import urllib.request
    from urllib.parse import urlencode

    base_url = f"https://api.x.com/2/users/{user_id}/tweets"
    params = {
        "max_results": str(MAX_RESULTS),
        "tweet.fields": "created_at",
    }
    url = f"{base_url}?{urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "OpenClawXTestTimeline/0.1",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body)


def main() -> None:
    load_env()

    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        print("Error: X_BEARER_TOKEN is not set in the environment.", file=sys.stderr)
        sys.exit(1)

    user_id = get_user_id_from_access_token()
    if not user_id:
        print(
            "Error: could not extract user ID from X_ACCESS_TOKEN (expected '<user_id>-...').",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        print(f"Fetching last {MAX_RESULTS} posts for user {user_id}...", file=sys.stderr)
        result = fetch_recent_tweets(user_id, bearer)
    except Exception as exc:
        print(f"Failure: exception during GET /2/users/:id/tweets — {exc}", file=sys.stderr)
        sys.exit(1)

    tweets: List[Dict[str, Any]] = result.get("data") or []

    if not tweets:
        print("No tweets returned.", file=sys.stderr)
    else:
        print(f"Retrieved {len(tweets)} tweets:\n")

    found_test = False
    for t in tweets:
        tid = t.get("id", "")
        text = t.get("text", "").replace("\n", " ")
        created_at = t.get("created_at", "")
        print(f"- id={tid} | created_at={created_at} | text={text}")
        if tid == KNOWN_TEST_TWEET_ID:
            found_test = True

    if KNOWN_TEST_TWEET_ID:
        if found_test:
            print(f"\nConfirmed: test post {KNOWN_TEST_TWEET_ID} appears in recent tweets.")
        else:
            print(f"\nNote: test post {KNOWN_TEST_TWEET_ID} not found in the last {MAX_RESULTS} tweets.")

    # Optionally, print raw JSON for debugging
    # print("\nRaw API response:")
    # print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

