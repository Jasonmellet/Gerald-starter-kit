#!/usr/bin/env python3
"""
One-off X API v2 test: fetch most recent direct messages in a conversation.

Requirements:
- Use the X DM conversation endpoint
- Return sender ID and message text
- Print results to console
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


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


def fetch_dm_messages(conversation_id: str, max_results: int = 10) -> Dict[str, Any]:
    """
    GET /2/dm_conversations/{id}/messages
    Returns raw JSON from the X API.
    """
    try:
        import requests  # type: ignore[import]
        from requests_oauthlib import OAuth1  # type: ignore[import]
    except Exception as exc:
        print(
            "Error: fetching DMs via OAuth 1.0a requires 'requests' and 'requests_oauthlib' packages.",
            file=sys.stderr,
        )
        raise

    creds = oauth1_creds()

    url = f"https://api.x.com/2/dm_conversations/{conversation_id}/messages"
    params = {"max_results": str(max_results)}

    auth = OAuth1(
        creds["api_key"],
        creds["api_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )

    resp = requests.get(
        url,
        params=params,
        auth=auth,
        timeout=15,
        headers={"User-Agent": "OpenClawXTestDMFetch/0.1"},
    )

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if not (200 <= resp.status_code < 300):
        print(
            f"X DM fetch API error {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        return data

    return data


def extract_messages(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract a simple list of {sender_id, text} entries from the DM payload.
    The exact shape of the response can vary; we handle common structures.
    """
    messages: List[Dict[str, Any]] = []

    # X DM v2 typically nests conversation events under "data" -> list of messages
    events = payload.get("data") or []

    for ev in events:
        # For v2 DM messages, expect fields like "sender_id" and "text"
        sender_id = ev.get("sender_id")
        text = ev.get("text")

        if sender_id and text:
            messages.append({"sender_id": sender_id, "text": text})

    return messages


def main() -> None:
    load_env()

    if len(sys.argv) < 2:
        print(
            "Usage: python3 tools/x_test_dm_fetch.py <dm_conversation_id>",
            file=sys.stderr,
        )
        sys.exit(1)

    conversation_id = sys.argv[1].strip()
    print(
        f"Fetching recent DMs in conversation {conversation_id}...",
        file=sys.stderr,
    )

    try:
        payload = fetch_dm_messages(conversation_id)
    except Exception as exc:
        print(f"Failure: exception while fetching DMs — {exc}", file=sys.stderr)
        sys.exit(1)

    messages = extract_messages(payload)

    if not messages:
        print("No DM messages parsed from response (see raw JSON below).")
        print(json.dumps(payload, indent=2))
        sys.exit(0)

    print(f"Found {len(messages)} messages:\n")
    for msg in messages:
        text_one_line = str(msg.get("text", "")).replace("\n", " ")
        print(f"- sender_id={msg.get('sender_id')} | text={text_one_line}")


if __name__ == "__main__":
    main()

