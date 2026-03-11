#!/usr/bin/env python3
"""
X (Twitter) OAuth 2.0 callback server — real callback URL for user auth.

Starts a small HTTP server that:
1. GET /x/start — redirects to X authorize URL (PKCE)
2. GET /x/callback — receives code, exchanges for tokens, saves to credentials/x_oauth_tokens.json

Requires in .env:
  X_CLIENT_ID          — from X Developer Portal (Keys and tokens)
  X_CALLBACK_BASE_URL  — your real HTTPS base (e.g. https://abc.ngrok-free.app or https://yourdomain.com), no trailing slash

Add this exact callback in X Developer Portal → your app → Callback URLs:
  {X_CALLBACK_BASE_URL}/x/callback

Usage:
  python3 tools/x_oauth_callback_server.py --port 8765
  # Then expose 8765 with ngrok, set X_CALLBACK_BASE_URL to the ngrok URL, add /x/callback in X portal, open /x/start in browser
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Repo root and .env
REPO_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_DIR = REPO_ROOT / "credentials"
TOKENS_FILE = CREDENTIALS_DIR / "x_oauth_tokens.json"


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
CALLBACK_BASE = (os.environ.get("X_CALLBACK_BASE_URL") or "").rstrip("/")
CLIENT_SECRET = os.environ.get("X_CLIENT_SECRET")  # optional, for confidential clients

# PKCE code_verifier storage (in-memory; keyed by state)
_pkce_store = {}

# Default scopes: read tweets/users, DMs, + offline access for refresh token
# Override with X_OAUTH_SCOPES in .env to e.g. drop DM if app doesn't have DM permission yet: tweet.read users.read offline.access
DEFAULT_SCOPE = os.environ.get("X_OAUTH_SCOPES") or "tweet.read users.read dm.read dm.write offline.access"


def pkce_verifier_and_challenge():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


def run_server(port: int):
    try:
        from flask import Flask, redirect, request
    except ImportError:
        print("Install Flask: pip install flask", file=__import__("sys").stderr)
        raise SystemExit(1)

    if not CLIENT_ID or not CALLBACK_BASE:
        print("Set X_CLIENT_ID and X_CALLBACK_BASE_URL in .env (repo root)", file=__import__("sys").stderr)
        raise SystemExit(1)

    redirect_uri = f"{CALLBACK_BASE}/x/callback"
    app = Flask(__name__)

    @app.route("/x/start")
    def x_start():
        state = secrets.token_urlsafe(16)
        verifier, challenge = pkce_verifier_and_challenge()
        _pkce_store[state] = verifier
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": DEFAULT_SCOPE,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = "https://x.com/i/oauth2/authorize?" + urllib.parse.urlencode(params)
        return redirect(url)

    @app.route("/x/callback")
    def x_callback():
        code = request.args.get("code")
        state = request.args.get("state")
        if not code or not state:
            return "Missing code or state", 400
        verifier = _pkce_store.pop(state, None)
        if not verifier:
            return "Invalid or expired state. Start again from /x/start", 400
        # Exchange code for tokens (OAuth 2.0 PKCE)
        body = urllib.parse.urlencode({
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
            "client_id": CLIENT_ID,
        })
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if CLIENT_SECRET:
            auth = base64.urlsafe_b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
            headers["Authorization"] = f"Basic {auth}"
        req = urllib.request.Request(
            "https://api.x.com/2/oauth2/token",
            data=body.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                tokens = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            return f"Token exchange failed: {e.code}<pre>{err}</pre>", 400
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        return (
            "<h1>X OAuth done</h1><p>Tokens saved to credentials/x_oauth_tokens.json</p>"
            "<p>You can close this tab.</p>"
        )

    print(f"Callback server: {CALLBACK_BASE}/x/callback")
    print(f"Start OAuth: {CALLBACK_BASE}/x/start")
    app.run(host="0.0.0.0", port=port, debug=False)


def main():
    p = argparse.ArgumentParser(description="X OAuth 2.0 callback server")
    p.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = p.parse_args()
    run_server(args.port)


if __name__ == "__main__":
    main()
