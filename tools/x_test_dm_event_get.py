#!/usr/bin/env python3
"""
One-off X API v2 test: fetch a single DM event by ID.

Endpoint (as per docs):
  GET /2/dm_events/{event_id}

Auth:
  OAuth 2.0 user token (we use X_USER_ACCESS_TOKEN from .env).

Usage:
  python3 tools/x_test_dm_event_get.py <dm_event_id>
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


def get_dm_event(event_id: str, user_token: str) -> Dict[str, Any]:
    """GET /2/dm_events/{event_id}."""
    import urllib.request

    url = f"https://api.x.com/2/dm_events/{event_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {user_token}",
            "User-Agent": "OpenClawXTestDMEventGet/0.1",
        },
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body)


def main() -> None:
    load_env()

    if len(sys.argv) < 2:
        print("Usage: python3 tools/x_test_dm_event_get.py <dm_event_id>", file=sys.stderr)
        sys.exit(1)

    dm_event_id = sys.argv[1].strip()
    user_token = (os.environ.get("X_USER_ACCESS_TOKEN") or "").strip()

    if not user_token:
        print(
            "X_USER_ACCESS_TOKEN is not set; /2/dm_events/{id} requires an OAuth 2.0 user access token.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Fetching DM event {dm_event_id} via GET /2/dm_events/{dm_event_id} ...",
        file=sys.stderr,
    )

    try:
        payload = get_dm_event(dm_event_id, user_token)
    except Exception as exc:
        print(f"Failure: exception while calling /2/dm_events/{dm_event_id} — {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

