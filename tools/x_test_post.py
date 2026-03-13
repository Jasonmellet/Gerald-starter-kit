#!/usr/bin/env python3
"""
One-off X API v2 test: publish a single post using authenticated credentials.

Behavior:
- Text: "Gerald automation test #1"
- Uses X_USER_ACCESS_TOKEN (OAuth 2.0 user bearer) if present,
  otherwise falls back to OAuth 1.0a user context
  (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET).
- Prints success/failure and the post ID returned by the API.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


POST_TEXT = "Gerald automation test #1"


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


def post_with_bearer(text: str, token: str) -> Dict[str, Any]:
    """POST /2/tweets using a user bearer token (X_USER_ACCESS_TOKEN)."""
    import urllib.request

    url = "https://api.x.com/2/tweets"
    payload = {"text": text}
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "OpenClawXTestPost/0.1",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body)


def post_with_oauth1(text: str) -> Dict[str, Any]:
    """POST /2/tweets using OAuth 1.0a user context."""
    try:
        import requests  # type: ignore[import]
        from requests_oauthlib import OAuth1  # type: ignore[import]
    except Exception as exc:
        print(
            "Error: posting via OAuth 1.0a requires 'requests' and 'requests_oauthlib' packages.",
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
    payload: Dict[str, Any] = {"text": text}

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
        headers={"Content-Type": "application/json", "User-Agent": "OpenClawXTestPost/0.1"},
    )

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if not (200 <= resp.status_code < 300):
        print(
            f"X API error {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        return data

    return data


def main() -> None:
    load_env()

    user_token = (os.environ.get("X_USER_ACCESS_TOKEN") or "").strip()

    try:
        if user_token:
            print("Posting to X using X_USER_ACCESS_TOKEN...", file=sys.stderr)
            result = post_with_bearer(POST_TEXT, user_token)
        else:
            print("Posting to X using OAuth 1.0a credentials...", file=sys.stderr)
            result = post_with_oauth1(POST_TEXT)
    except Exception as exc:
        print(f"Failure: exception while posting — {exc}", file=sys.stderr)
        sys.exit(1)

    data = (result or {}).get("data") or {}
    tweet_id = data.get("id")

    if tweet_id:
        print(f"Success: posted to X with ID {tweet_id}")
        # Also emit raw JSON for debugging if needed
        print(json.dumps(result, indent=2))
        sys.exit(0)

    print("Failure: no tweet ID returned by X API", file=sys.stderr)
    print(json.dumps(result, indent=2))
    sys.exit(1)


if __name__ == "__main__":
    main()

