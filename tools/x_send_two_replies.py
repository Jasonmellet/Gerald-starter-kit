#!/usr/bin/env python3
"""One-off: send the two approved replies. Run from repo root with PYTHONPATH=tools."""
import sys
sys.path.insert(0, "tools")
from x_system.x_client import XClient

REPLIES = [
    ("2031910557117530295", "We're poking at this at allgreatthings.io ... helping teams actually use agent-style workflows in revops instead of just watching demos. Still early but would love to be in the mix."),
    ("2032345595675808131", "That bar ... sales ops can ship it without a dev ... is the one that actually scales. Nice to see someone designing for that."),
]

def main():
    client = XClient()
    for tweet_id, text in REPLIES:
        try:
            out = client.reply_to_tweet(tweet_id, text)
            new_id = (out or {}).get("data", {}).get("id")
            print(f"OK reply to {tweet_id} -> {new_id}")
        except Exception as e:
            print(f"FAIL reply to {tweet_id}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
