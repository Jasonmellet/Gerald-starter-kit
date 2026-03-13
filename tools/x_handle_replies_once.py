#!/usr/bin/env python3
"""
One-off handler: for an existing tweet, find the latest reply, reply to it,
and send a DM to that user.

Usage:
  python3 tools/x_handle_replies_once.py <tweet_id>
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def search_replies(tweet_id: str, bearer_token: str) -> Dict[str, Any]:
    """
    Use recent search to find replies in the same conversation as the tweet.
    Query: conversation_id:<tweet_id> is:reply
    """
    import urllib.request
    from urllib.parse import urlencode

    base_url = "https://api.x.com/2/tweets/search/recent"
    query = f"conversation_id:{tweet_id} is:reply"

    params = {
        "query": query,
        "max_results": "50",
        "tweet.fields": "author_id,created_at,conversation_id,in_reply_to_user_id",
    }

    url = f"{base_url}?{urlencode(params)}"
    print(f"[1] Fetching replies via recent search: {url}")

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "OpenClawXHandleRepliesOnce/0.1",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body)


def reply_to_tweet(in_reply_to_tweet_id: str, text: str) -> Optional[str]:
    """POST /2/tweets with reply object using OAuth 1.0a. Returns reply tweet_id or None."""
    try:
        import requests  # type: ignore[import]
        from requests_oauthlib import OAuth1  # type: ignore[import]
    except Exception as exc:
        print(
            "Error: replying via OAuth 1.0a requires 'requests' and 'requests_oauthlib' packages.",
            file=sys.stderr,
        )
        print(f"Underlying error: {exc}", file=sys.stderr)
        return None

    creds = oauth1_creds()

    url = "https://api.x.com/2/tweets"
    payload: Dict[str, Any] = {
        "text": text,
        "reply": {
            "in_reply_to_tweet_id": in_reply_to_tweet_id,
            "auto_populate_reply_metadata": True,
        },
    }

    auth = OAuth1(
        creds["api_key"],
        creds["api_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )

    print(f"[2] Replying to tweet {in_reply_to_tweet_id} with text: {text!r}")
    resp = requests.post(
        url,
        json=payload,
        auth=auth,
        timeout=15,
        headers={"Content-Type": "application/json", "User-Agent": "OpenClawXHandleRepliesOnce/0.1"},
    )

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if not (200 <= resp.status_code < 300):
        print(f"[2] X API reply error {resp.status_code}: {resp.text}", file=sys.stderr)
        print(json.dumps(data, indent=2))
        return None

    reply_id = (data or {}).get("data", {}).get("id")
    print(f"[2] Success: posted reply with ID {reply_id}")
    return reply_id


def send_dm(recipient_user_id: str, text: str) -> Optional[str]:
    """Send DM via POST /2/dm_conversations/with/{participant_id}/messages. Returns dm_event_id or None."""
    try:
        import requests  # type: ignore[import]
        from requests_oauthlib import OAuth1  # type: ignore[import]
    except Exception as exc:
        print(
            "Error: sending DMs via OAuth 1.0a requires 'requests' and 'requests_oauthlib' packages.",
            file=sys.stderr,
        )
        print(f"Underlying error: {exc}", file=sys.stderr)
        return None

    creds = oauth1_creds()

    url = f"https://api.x.com/2/dm_conversations/with/{recipient_user_id}/messages"
    payload: Dict[str, Any] = {"text": text}

    auth = OAuth1(
        creds["api_key"],
        creds["api_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )

    print(f"[3] Sending DM to user {recipient_user_id} with text: {text!r}")
    resp = requests.post(
        url,
        json=payload,
        auth=auth,
        timeout=15,
        headers={"Content-Type": "application/json", "User-Agent": "OpenClawXHandleRepliesOnce/0.1"},
    )

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if not (200 <= resp.status_code < 300):
        print(f"[3] X DM API error {resp.status_code}: {resp.text}", file=sys.stderr)
        print(json.dumps(data, indent=2))
        return None

    dm_event_id = (data or {}).get("data", {}).get("dm_event_id")
    print(f"[3] Success: DM sent with event ID {dm_event_id}")
    return dm_event_id


def main() -> None:
    load_env()

    if len(sys.argv) < 2:
        print("Usage: python3 tools/x_handle_replies_once.py <tweet_id>", file=sys.stderr)
        sys.exit(1)

    tweet_id = sys.argv[1].strip()
    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        print("Error: X_BEARER_TOKEN is not set in the environment.", file=sys.stderr)
        sys.exit(1)

    # 1. Fetch replies
    print(f"[1] Looking for replies to tweet {tweet_id}...")
    try:
        payload = search_replies(tweet_id, bearer)
    except Exception as exc:
        print(f"[1] Failure: exception during search — {exc}", file=sys.stderr)
        sys.exit(1)

    replies: List[Dict[str, Any]] = payload.get("data") or []
    if not replies:
        print("[1] No replies found yet for this tweet.")
        sys.exit(0)

    # Use the most recent reply (tweets are returned most-recent-first in search/recent)
    first_reply = replies[0]
    reply_tweet_id = first_reply.get("id")
    author_id = first_reply.get("author_id")
    reply_text = first_reply.get("text", "").replace("\n", " ")
    print(f"[1] Latest reply tweet ID: {reply_tweet_id}, author_id: {author_id}, text: {reply_text!r}")

    if not reply_tweet_id or not author_id:
        print("[1] Reply missing id/author_id; cannot continue.", file=sys.stderr)
        sys.exit(1)

    # 2. Reply to the comment
    reply_body = "Love this—curious what part of that idea hits hardest for you right now?"
    reply_result_id = reply_to_tweet(reply_tweet_id, reply_body)
    if not reply_result_id:
        print("[2] Failed to post reply to comment; skipping DM step.", file=sys.stderr)
        sys.exit(1)

    # 3. Send a DM to the user
    dm_body = "Hey — appreciate you jumping into that thread. What are you actually working on with agents or automation these days?"
    dm_event_id = send_dm(author_id, dm_body)
    if not dm_event_id:
        print("[3] Failed to send DM after reply.", file=sys.stderr)
        sys.exit(1)

    print("[3] One-off handler completed: replied to latest comment and sent DM.")


if __name__ == "__main__":
    main()

