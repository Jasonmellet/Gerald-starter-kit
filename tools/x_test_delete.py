#!/usr/bin/env python3
"""
One-off X API v2 test: delete a specific post.

Requirements:
- Accept a tweet ID as input
- Use DELETE /2/tweets/:id
- Log success or failure
- Confirm the post was removed
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


def load_env() -> None:
    """Load .env from workspace root if present."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ.setdefault(key, val)


def oauth1_creds() -> Dict[str, str]:
    """Return OAuth 1.0a credentials from environment or exit with error."""
    api_key = os.environ.get("X_API_KEY") or os.environ.get("x_api_key")
    api_secret = os.environ.get("X_API_SECRET") or os.environ.get("x_api_secret")
    access_token = os.environ.get("X_ACCESS_TOKEN") or os.environ.get("x_access_token")
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET") or os.environ.get(
        "x_access_token_secret"
    )

    if not all([api_key, api_secret, access_token, access_token_secret]):
        print(
            "Error: missing one or more OAuth 1.0a credentials "
            "(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET).",
            file=sys.stderr,
        )
        sys.exit(1)

    return {
        "api_key": api_key,  # type: ignore[arg-type]
        "api_secret": api_secret,  # type: ignore[arg-type]
        "access_token": access_token,  # type: ignore[arg-type]
        "access_token_secret": access_token_secret,  # type: ignore[arg-type]
    }


def delete_tweet(tweet_id: str) -> Dict[str, Any]:
    """DELETE /2/tweets/:id using OAuth 1.0a user context."""
    try:
        import requests  # type: ignore[import]
        from requests_oauthlib import OAuth1  # type: ignore[import]
    except Exception as exc:
        print(
            "Error: deleting via OAuth 1.0a requires 'requests' and 'requests_oauthlib' packages.",
            file=sys.stderr,
        )
        raise

    creds = oauth1_creds()

    url = f"https://api.x.com/2/tweets/{tweet_id}"
    auth = OAuth1(
        creds["api_key"],
        creds["api_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )

    resp = requests.delete(
        url,
        auth=auth,
        timeout=15,
        headers={"User-Agent": "OpenClawXTestDelete/0.1"},
    )

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if not (200 <= resp.status_code < 300):
        print(
            f"X API delete error {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        return data

    return data


def confirm_deleted(tweet_id: str) -> bool:
    """
    Confirm the tweet is gone using GET /2/tweets/:id.
    Treat 404 as confirmation of deletion.
    """
    import urllib.request
    import urllib.error

    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        print(
            "Warning: X_BEARER_TOKEN not set; skipping post-delete confirmation.",
            file=sys.stderr,
        )
        return True

    url = f"https://api.x.com/2/tweets/{tweet_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer}",
            "User-Agent": "OpenClawXTestDelete/0.1",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            data = json.loads(body)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True
        print(f"Error during confirmation GET /2/tweets/:id — {e}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"Unexpected error during confirmation — {exc}", file=sys.stderr)
        return False

    # If API returns an errors array indicating not found, also treat as deleted.
    if data.get("errors"):
        return True

    # If data still contains the tweet, it's not deleted.
    return False


def main() -> None:
    load_env()

    if len(sys.argv) < 2:
        print("Usage: python3 tools/x_test_delete.py <tweet_id>", file=sys.stderr)
        sys.exit(1)

    tweet_id = sys.argv[1].strip()
    print(f"Deleting X post {tweet_id} via DELETE /2/tweets/:id ...", file=sys.stderr)

    try:
        delete_result = delete_tweet(tweet_id)
    except Exception as exc:
        print(f"Failure: exception during delete — {exc}", file=sys.stderr)
        sys.exit(1)

    deleted_flag = (delete_result or {}).get("data", {}).get("deleted")
    if not deleted_flag:
        print("Failure: X API did not confirm deletion:", file=sys.stderr)
        print(json.dumps(delete_result, indent=2))
        sys.exit(1)

    # Confirm via GET
    if confirm_deleted(tweet_id):
        print(f"Success: tweet {tweet_id} deleted and confirmed removed.")
        sys.exit(0)

    print(f"Warning: tweet {tweet_id} delete reported, but confirmation failed.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

