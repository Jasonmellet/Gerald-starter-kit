#!/usr/bin/env python3
"""
Test X API v2 POST /2/tweets (reply) with your OAuth 1.0a credentials.

Run from repo root with a real tweet ID you want to reply to (e.g. your own tweet):
  cd /Users/jcore/Desktop/Openclaw/gerald
  PYTHONPATH=. python3 scripts/test_reply_endpoint.py <TWEET_ID>

Example:
  PYTHONPATH=. python3 scripts/test_reply_endpoint.py 1234567890123456789

If you get 200: your app has tweet write access; safe to build the follow-up reply feature.
If you get 403/453: app needs "Read and write" for Tweets in the developer portal.
"""

import os
import sys

# Load .env from gerald directory
script_dir = os.path.dirname(os.path.abspath(__file__))
gerald_dir = os.path.dirname(script_dir)
env_path = os.path.join(gerald_dir, ".env")
if os.path.isfile(env_path):
    from dotenv import load_dotenv
    load_dotenv(env_path)

# Add gerald to path so we can use app.config
sys.path.insert(0, gerald_dir)


def main():
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python3 scripts/test_reply_endpoint.py <TWEET_ID>", file=sys.stderr)
        print("  Reply to one of your own tweets first to test.", file=sys.stderr)
        sys.exit(1)

    tweet_id = sys.argv[1].strip()
    if not tweet_id.isdigit():
        print("TWEET_ID must be numeric.", file=sys.stderr)
        sys.exit(1)

    from app.config import get_settings
    settings = get_settings()
    api_key = settings.x_api_key
    api_secret = settings.x_api_secret
    access_token = settings.x_access_token
    access_token_secret = settings.x_access_token_secret

    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("Missing X OAuth credentials in .env (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)", file=sys.stderr)
        sys.exit(1)

    try:
        import requests
        from requests_oauthlib import OAuth1
    except ImportError:
        print("Install: pip install requests requests_oauthlib", file=sys.stderr)
        sys.exit(1)

    url = "https://api.x.com/2/tweets"
    payload = {
        "text": "Test reply from Gerald – you can delete this.",
        "reply": {"in_reply_to_tweet_id": tweet_id},
    }
    auth = OAuth1(api_key, api_secret, access_token, access_token_secret)

    print(f"POST {url} (reply to tweet {tweet_id}) ...")
    resp = requests.post(url, json=payload, auth=auth, timeout=10, headers={"Content-Type": "application/json"})
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")

    if 200 <= resp.status_code < 300:
        print("\nSuccess. Your app can post replies; safe to build the follow-up feature.")
    else:
        print("\nFailed. If 403/453: add 'Read and write' for Tweets in the X developer portal for this app.")


if __name__ == "__main__":
    main()
