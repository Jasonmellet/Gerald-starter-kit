#!/usr/bin/env python3
"""
Send a direct message on X (Twitter) using your OAuth user tokens.

Requires: credentials/x_oauth_tokens.json (from completing the X OAuth flow with dm.read + dm.write scopes).
If you only had tweet.read/users.read before, re-run the OAuth flow once so the new tokens include DM scope:
  Open https://gerald-says-hi.ngrok.io/x/start (with Flask + ngrok running).

Usage:
  python3 tools/x_dm.py @username "Your message here"
  python3 tools/x_dm.py username "Your message here"
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKENS_FILE = REPO_ROOT / "credentials" / "x_oauth_tokens.json"
BASE_URL = "https://api.x.com/2"


def load_env():
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


load_env()
CLIENT_ID = os.environ.get("X_CLIENT_ID")


def load_tokens():
    if not TOKENS_FILE.exists():
        print("No OAuth tokens found. Run the X OAuth flow first (open /x/start with Flask + ngrok running).", file=sys.stderr)
        sys.exit(1)
    with open(TOKENS_FILE) as f:
        return json.load(f)


def refresh_access_token(tokens):
    """Get a new access_token using refresh_token."""
    if not CLIENT_ID or "refresh_token" not in tokens:
        return None
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": CLIENT_ID,
    })
    req = urllib.request.Request(
        f"{BASE_URL}/oauth2/token",
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            new_tokens = json.loads(resp.read().decode())
            new_tokens.setdefault("refresh_token", tokens.get("refresh_token"))
            with open(TOKENS_FILE, "w") as f:
                json.dump(new_tokens, f, indent=2)
            return new_tokens
    except Exception:
        return None


def get_user_id_by_username(access_token: str, username: str) -> str:
    username = username.lstrip("@")
    req = urllib.request.Request(
        f"{BASE_URL}/users/by/username/{urllib.parse.quote(username)}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    if "data" not in data:
        raise ValueError(data.get("errors", [{}])[0].get("detail", "User not found"))
    return data["data"]["id"]


def send_dm(access_token: str, participant_id: str, text: str) -> dict:
    url = f"{BASE_URL}/dm_conversations/with/{participant_id}/messages"
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    username = sys.argv[1]
    message = " ".join(sys.argv[2:]).strip()
    if not message:
        print("Provide a message.", file=sys.stderr)
        sys.exit(1)

    tokens = load_tokens()
    access_token = tokens.get("access_token")
    if not access_token:
        print("No access_token in credentials. Re-run the OAuth flow (/x/start).", file=sys.stderr)
        sys.exit(1)

    try:
        user_id = get_user_id_by_username(access_token, username)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # Try refresh
            new_tokens = refresh_access_token(tokens)
            if new_tokens:
                access_token = new_tokens["access_token"]
                user_id = get_user_id_by_username(access_token, username)
            else:
                print("Token expired. Re-run OAuth: open https://gerald-says-hi.ngrok.io/x/start", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"User lookup failed: {e.read().decode()}", file=sys.stderr)
            sys.exit(1)

    try:
        result = send_dm(access_token, user_id, message)
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        if e.code == 401:
            new_tokens = refresh_access_token(tokens)
            if new_tokens:
                result = send_dm(new_tokens["access_token"], user_id, message)
            else:
                print("Token expired. Re-run OAuth: open https://gerald-says-hi.ngrok.io/x/start", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Send DM failed: {e.code} {err}", file=sys.stderr)
            sys.exit(1)

    print("DM sent.")
    if result.get("data"):
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
