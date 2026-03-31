#!/usr/bin/env python3
"""
One-off X API v2 test: fetch recent DM events across all conversations.

Endpoint: GET /2/dm_events
Auth: OAuth 2.0 user token (X_USER_ACCESS_TOKEN)

If X_USER_ACCESS_TOKEN is not configured, the script will explain what is missing.
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


def fetch_dm_events(user_token: str, max_results: int = 20) -> Dict[str, Any]:
    """GET /2/dm_events using a user bearer token."""
    import urllib.request
    from urllib.parse import urlencode

    base_url = "https://api.x.com/2/dm_events"
    params = {
        "max_results": str(max_results),
        "event_types": "MessageCreate",
        "dm_event.fields": "id,dm_conversation_id,sender_id,text,created_at",
    }
    url = f"{base_url}?{urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {user_token}",
            "User-Agent": "OpenClawXTestDMEvents/0.1",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body)


def extract_messages(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract a list of {sender_id, text, dm_conversation_id} from DM events.
    """
    messages: List[Dict[str, Any]] = []
    events = payload.get("data") or []

    for ev in events:
        if ev.get("event_type") != "MessageCreate":
            continue
        sender_id = ev.get("sender_id")
        text = ev.get("text")
        conv_id = ev.get("dm_conversation_id")
        if sender_id and text:
            messages.append(
                {
                    "sender_id": sender_id,
                    "text": text,
                    "dm_conversation_id": conv_id,
                }
            )
    return messages


def main() -> None:
    load_env()

    user_token = (os.environ.get("X_USER_ACCESS_TOKEN") or "").strip()
    if not user_token:
        print(
            "X_USER_ACCESS_TOKEN is not set. The /2/dm_events endpoint requires an OAuth 2.0 user access token.\n"
            "Run the X OAuth 2.0 PKCE / user access flow once, then add the resulting access token as X_USER_ACCESS_TOKEN in .env.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        print("Fetching recent DM events via GET /2/dm_events ...", file=sys.stderr)
        payload = fetch_dm_events(user_token)
    except Exception as exc:
        print(f"Failure: exception while calling /2/dm_events — {exc}", file=sys.stderr)
        sys.exit(1)

    messages = extract_messages(payload)

    if not messages:
        print("No MessageCreate events found in response (see raw JSON below).")
        print(json.dumps(payload, indent=2))
        sys.exit(0)

    print(f"Found {len(messages)} DM events:\n")
    for msg in messages:
        text_one_line = str(msg.get("text", "")).replace("\n", " ")
        print(
            f"- sender_id={msg.get('sender_id')} | dm_conversation_id={msg.get('dm_conversation_id')} | text={text_one_line}"
        )


if __name__ == "__main__":
    main()

