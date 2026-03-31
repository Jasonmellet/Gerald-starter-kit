#!/usr/bin/env python3
"""
Post to X (Twitter) via API v2 using your account.

Usage:
  # Create a new post
  python3 tools/x_post.py "Hello from OpenClaw"

  # Delete a post by ID
  python3 tools/x_post.py delete 2032526257468952862

If no text argument is provided for create, reads the post text from stdin.

Auth strategy:
- Use OAuth 1.0a user context:
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def load_env() -> None:
    """
    Load .env from workspace root if present.
    Mirrors tools/x_api_client.py behavior.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ.setdefault(key, val)


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
            "User-Agent": "OpenClawXPoster/0.1",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            return json.loads(body)
    except Exception as exc:
        print(f"Error posting with bearer token: {exc}", file=sys.stderr)
        raise


def oauth1_creds() -> Optional[Dict[str, str]]:
    """
    Load OAuth 1.0a credentials from environment.
    Returns dict or None if incomplete.
    """
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


def post_with_oauth1(text: str) -> Dict[str, Any]:
    """
    POST /2/tweets using OAuth 1.0a user context.
    Requires requests and requests_oauthlib (same as DM helper).
    """
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
        headers={"Content-Type": "application/json", "User-Agent": "OpenClawXPoster/0.1"},
    )

    if not (200 <= resp.status_code < 300):
        print(
            f"X API error {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        try:
            return resp.json()
        except ValueError:
            sys.exit(1)

    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


def delete_with_oauth1(tweet_id: str) -> Dict[str, Any]:
    """
    DELETE /2/tweets/:id using OAuth 1.0a user context.
    Only works for posts authored by this account.
    """
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
    if not creds:
        print(
            "Error: missing one or more OAuth 1.0a credentials "
            "(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET).",
            file=sys.stderr,
        )
        sys.exit(1)

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
        headers={"User-Agent": "OpenClawXPoster/0.1"},
    )

    if not (200 <= resp.status_code < 300):
        print(
            f"X API delete error {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        try:
            return resp.json()
        except ValueError:
            sys.exit(1)

    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


def main() -> None:
    load_env()

    # Subcommand: delete <tweet_id>
    if len(sys.argv) >= 3 and sys.argv[1] == "delete":
        tweet_id = sys.argv[2]
        print(f"Deleting X post {tweet_id} using OAuth 1.0a credentials...", file=sys.stderr)
        result = delete_with_oauth1(tweet_id)
        print(json.dumps(result, indent=2))
        return

    # Default: create a new post (always via OAuth 1.0a, which we know works)
    if len(sys.argv) >= 2:
        text = " ".join(sys.argv[1:]).strip()
    else:
        print("Enter post text, then Ctrl-D (Ctrl-Z on Windows):", file=sys.stderr)
        text = sys.stdin.read().strip()

    if not text:
        print("Error: post text cannot be empty.", file=sys.stderr)
        sys.exit(1)

    try:
        print("Posting to X using OAuth 1.0a credentials...", file=sys.stderr)
        result = post_with_oauth1(text)
    except Exception:
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

