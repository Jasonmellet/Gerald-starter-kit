#!/usr/bin/env python3
"""
One-off X API v2 test: send a direct message to a specific user.

Requirements:
- Input: user ID
- Message text: "Hey — thanks for engaging with my post earlier." (default) or custom text
- Use POST /2/dm_conversations/with/:participant_id/messages
- Log success or failure
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


def send_dm(recipient_user_id: str) -> Dict[str, Any]:
    """POST /2/dm_conversations/with/{participant_id}/messages using OAuth 1.0a user context."""
    try:
        import requests  # type: ignore[import]
        from requests_oauthlib import OAuth1  # type: ignore[import]
    except Exception as exc:
        print(
            "Error: sending DMs via OAuth 1.0a requires 'requests' and 'requests_oauthlib' packages.",
            file=sys.stderr,
        )
        raise

    creds = oauth1_creds()

    url = f"https://api.x.com/2/dm_conversations/with/{recipient_user_id}/messages"
    # Message text is passed in via function argument to allow custom messages per test.
    payload: Dict[str, Any] = {"text": MESSAGE_TEXT}

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
        headers={"Content-Type": "application/json", "User-Agent": "OpenClawXTestDM/0.1"},
    )

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if not (200 <= resp.status_code < 300):
        print(
            f"X DM API error {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        return data

    return data


def main() -> None:
    load_env()

    if len(sys.argv) < 2:
        print(
            "Usage: python3 tools/x_test_dm.py <recipient_user_id> [custom message text]",
            file=sys.stderr,
        )
        sys.exit(1)

    recipient_user_id = sys.argv[1].strip()
    global MESSAGE_TEXT
    if len(sys.argv) >= 3:
        MESSAGE_TEXT = " ".join(sys.argv[2:]).strip()

    print(
        f"Sending test DM to user {recipient_user_id} via POST /2/dm_conversations/with/:participant_id/messages ...",
        file=sys.stderr,
    )

    try:
        result = send_dm(recipient_user_id)
    except Exception as exc:
        print(f"Failure: exception while sending DM — {exc}", file=sys.stderr)
        sys.exit(1)

    data = (result or {}).get("data") or {}
    dm_event_id = data.get("dm_event_id")

    if dm_event_id:
        print(f"Success: DM sent with event ID {dm_event_id}")
        print(json.dumps(result, indent=2))
        sys.exit(0)

    print("Failure: DM API did not return a dm_event_id", file=sys.stderr)
    print(json.dumps(result, indent=2))
    sys.exit(1)


if __name__ == "__main__":
    main()

