#!/usr/bin/env python3
"""
One-off X API v2 test: reply to a specific tweet.

Requirements:
- Input: tweet ID
- Post reply text: "Thanks for the comment — curious what made you interested in this?"
- Use POST /2/tweets
- Include the reply settings referencing the tweet ID
- Print success or failure
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


REPLY_TEXT = "Thanks for the comment — curious what made you interested in this?"


def load_env() -> None:
    """Load .env from workspace root if present."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ.setdefault(key, val)


def oauth1_creds() -> Optional[Dict[str, str]]:
    """Return OAuth 1.0a credentials from environment if all are present."""
    api_key = os.environ.get("X_API_KEY") or os.environ.get("x_api_key")
    api_secret = os.environ.get("X_API_SECRET") or os.environ.get("x_api_secret")
    access_token = os.environ.get("X_ACCESS_TOKEN") or os.environ.get("x_access_token")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET") or os.environ.get(
        "x_access_token_secret"
    )

    if not all([api_key, api_secret, access_token, access_token_secret]):
        return None

    return {
        "api_key": api_key,  # type: ignore[arg-type]
        "api_secret": api_secret,  # type: ignore[arg-type]
        "access_token": access_token,  # type: ignore[arg-type]
        "access_token_secret": access_token_secret,  # type: ignore[arg-type]
    }


def reply_with_bearer(in_reply_to_id: str, token: str) -> Dict[str, Any]:
    """POST /2/tweets with reply object using a user bearer token (X_USER_ACCESS_TOKEN)."""
    import urllib.request

    url = "https://api.x.com/2/tweets"
    payload: Dict[str, Any] = {
        "text": REPLY_TEXT,
        "reply": {
            "in_reply_to_tweet_id": in_reply_to_id,
            "auto_populate_reply_metadata": True,
        },
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "OpenClawXTestReply/0.1",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body)


def reply_with_oauth1(in_reply_to_id: str) -> Dict[str, Any]:
    """POST /2/tweets with reply object using OAuth 1.0a user context."""
    try:
        import requests  # type: ignore[import]
        from requests_oauthlib import OAuth1  # type: ignore[import]
    except Exception as exc:
        print(
            "Error: replying via OAuth 1.0a requires 'requests' and 'requests_oauthlib' packages.",
            file=sys.stderr,
        )
        raise

    creds = oauth1_creds()
    if not creds:
        print(
            "Error: missing one or more OAuth 1.0a credentials "
            "(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET).",
            file=sys.stderr,
        )
        sys.exit(1)

    url = "https://api.x.com/2/tweets"
    payload: Dict[str, Any] = {
        "text": REPLY_TEXT,
        "reply": {
            "in_reply_to_tweet_id": in_reply_to_id,
            "auto_populate_reply_metadata": True,
        },
    }

    auth = OAuth1(
        creds["api_key"],
        creds["api_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )

    resp = requests.post(
        url,
        json=payload,
        auth=auth,
        timeout=15,
        headers={"Content-Type": "application/json", "User-Agent": "OpenClawXTestReply/0.1"},
    )

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if not (200 <= resp.status_code < 300):
        print(
            f"X API reply error {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        return data

    return data


def main() -> None:
    load_env()

    if len(sys.argv) < 2:
        print("Usage: python3 tools/x_test_reply.py <tweet_id>", file=sys.stderr)
        sys.exit(1)

    tweet_id = sys.argv[1].strip()
    user_token = (os.environ.get("X_USER_ACCESS_TOKEN") or "").strip()

    try:
        if user_token:
            print(
                f"Replying to tweet {tweet_id} using X_USER_ACCESS_TOKEN...",
                file=sys.stderr,
            )
            result = reply_with_bearer(tweet_id, user_token)
        else:
            print(
                f"Replying to tweet {tweet_id} using OAuth 1.0a credentials...",
                file=sys.stderr,
            )
            result = reply_with_oauth1(tweet_id)
    except Exception as exc:
        print(f"Failure: exception while replying — {exc}", file=sys.stderr)
        sys.exit(1)

    data = (result or {}).get("data") or {}
    reply_id = data.get("id")

    if reply_id:
        print(f"Success: posted reply with ID {reply_id}")
        print(json.dumps(result, indent=2))
        sys.exit(0)

    print("Failure: no reply tweet ID returned by X API", file=sys.stderr)
    print(json.dumps(result, indent=2))
    sys.exit(1)


if __name__ == "__main__":
    main()

