#!/usr/bin/env python3
"""
One-off: fetch a tweet by ID, generate a short reply with the follow-up LLM, post it.
Usage: PYTHONPATH=. python scripts/reply_to_tweet.py <tweet_id>
Example: PYTHONPATH=. python scripts/reply_to_tweet.py 2024253386623742173
"""
from __future__ import annotations

import sys

# Allow importing app from repo root
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from app.clients.x_client import XClient, XClientError
from app.services.follow_up_reply_service import _generate_question


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python scripts/reply_to_tweet.py <tweet_id>", file=sys.stderr)
        sys.exit(1)
    tweet_id = sys.argv[1].strip()
    if not tweet_id.isdigit():
        print("tweet_id must be numeric", file=sys.stderr)
        sys.exit(1)

    client = XClient()
    tweet = client.get_tweet(tweet_id)
    if not tweet:
        print("Tweet not found or not accessible.", file=sys.stderr)
        sys.exit(1)
    text = (tweet.get("text") or "").strip()
    if not text:
        print("Tweet has no text.", file=sys.stderr)
        sys.exit(1)
    print("Tweet text:", repr(text[:200] + ("..." if len(text) > 200 else "")))

    question = _generate_question(text)
    if not question:
        print("Could not generate a reply.", file=sys.stderr)
        sys.exit(1)
    print("Posting reply:", repr(question))

    try:
        result = client.create_reply(in_reply_to_tweet_id=tweet_id, text=question)
        new_id = result.get("tweet_id")
        if new_id:
            print("Reply posted. Tweet ID:", new_id)
            print("https://x.com/i/status/" + str(new_id))
        else:
            print("Reply API returned no tweet id.", file=sys.stderr)
            sys.exit(1)
    except XClientError as e:
        print("X API error:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
