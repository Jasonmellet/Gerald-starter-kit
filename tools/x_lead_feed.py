#!/usr/bin/env python3
"""
X (Twitter) lead feed for Gerald.
Runs search queries and writes results to memory/x_lead_feed.json
so Gerald can read the file and suggest who to contact and what to say.

Usage:
  python3 tools/x_lead_feed.py
  python3 tools/x_lead_feed.py "fractional CMO OR \"need marketing help\""

If no query given, uses X_LEAD_QUERIES from .env (comma-separated)
or default: "fractional CMO", "looking for marketing help", "AI agent builder"
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = REPO_ROOT / "memory" / "x_lead_feed.json"

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

# Import after env is loaded
sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_api_client import search_recent

DEFAULT_QUERIES = [
    # Early-stage startup signals
    "seed round marketing",
    "Series A marketing",
    "just raised funding marketing",
    "startup first marketing hire",
    "early stage startup marketing",
    "pre-seed marketing help",
    "newly funded startup",
    # Original queries
    "fractional CMO",
    "looking for marketing help",
    "AI agent builder",
    "first marketing hire",
]

def run():
    if len(sys.argv) >= 2:
        queries = [sys.argv[1]]
    else:
        raw = os.environ.get("X_LEAD_QUERIES", "")
        queries = [q.strip() for q in raw.split(",") if q.strip()] if raw else DEFAULT_QUERIES

    all_leads = []
    max_per_query = min(15, max(10, 100 // len(queries)))

    for query in queries:
        try:
            result = search_recent(query, max_results=max_per_query)
        except Exception as e:
            print(f"Search '{query}' failed: {e}", file=sys.stderr)
            continue

        data = result.get("data") or []
        users = {u["id"]: u for u in result.get("includes", {}).get("users", [])}

        for tweet in data:
            # Skip retweets
            if tweet.get("text", "").startswith("RT @"):
                continue
            
            author = users.get(tweet.get("author_id"), {})
            username = author.get("username", "unknown")
            text = tweet.get("text", "").lower()
            full_text = tweet.get("text", "")
            
            # Score for startup signals
            startup_score = 0
            startup_signals = []
            
            # High-value signals (founder/CMO perspective)
            if any(term in text for term in ["we just raised", "we raised", "announcing our seed", "announcing our series a", "closing our round"]):
                startup_score += 5
                startup_signals.append("recent_funding")
            
            if any(term in text for term in ["first marketing hire", "first hire", "building our team", "hiring our first"]):
                startup_score += 5
                startup_signals.append("early_hire")
            
            if any(term in text for term in ["i'm the founder", "i'm a founder", "my startup", "our startup"]):
                startup_score += 4
                startup_signals.append("founder_voice")
            
            if any(term in text for term in ["need marketing help", "looking for marketing", "marketing hire", "growth hire"]):
                startup_score += 4
                startup_signals.append("active_marketing_need")
            
            # Medium-value signals
            if any(term in text for term in ["early stage", "pre-seed", "seed stage", "series a"]):
                startup_score += 2
                startup_signals.append("startup_stage")
            
            # Skip low-quality leads (just mentioning keywords without context)
            if startup_score < 2:
                continue
            
            lead = {
                "tweet_id": tweet.get("id"),
                "text": full_text,
                "author_username": username,
                "author_id": tweet.get("author_id"),
                "link": f"https://x.com/{username}/status/{tweet.get('id')}" if tweet.get("id") else "",
                "created_at": tweet.get("created_at", ""),
                "like_count": tweet.get("public_metrics", {}).get("like_count", 0),
                "reply_count": tweet.get("public_metrics", {}).get("reply_count", 0),
                "retweet_count": tweet.get("public_metrics", {}).get("retweet_count", 0),
                "query": query,
                "startup_score": startup_score,
                "startup_signals": startup_signals,
            }
            all_leads.append(lead)

    payload = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "queries": queries,
        "count": len(all_leads),
        "leads": all_leads,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {len(all_leads)} leads to {OUTPUT_FILE}")
    return 0

if __name__ == "__main__":
    sys.exit(run())
