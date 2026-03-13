from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import write_json_file
from .utils import clamp, utc_now_compact
from .x_client import XClient


ICP_KEYWORDS = [
    "founder",
    "ceo",
    "owner",
    "president",
    "head of sales",
    "head of marketing",
    "revenue",
    "revops",
    "sales ops",
    "crm",
    "pipeline",
    "lead gen",
    "seo",
    "ppc",
    "sem",
    "attribution",
    "outbound",
    "agency",
    "operations",
]

LOW_SIGNAL_KEYWORDS = [
    "giveaway",
    "airdrop",
    "gm",
    "follow for follow",
    "join my course",
    "pump",
    "crypto moon",
]


@dataclass
class ResearchResult:
    run_id: str
    items: List[Dict[str, Any]]
    artifact_path: Path


def _engagement_score(metrics: Dict[str, Any]) -> float:
    likes = float(metrics.get("like_count", 0))
    replies = float(metrics.get("reply_count", 0))
    retweets = float(metrics.get("retweet_count", 0))
    quotes = float(metrics.get("quote_count", 0))
    # Reply-heavy weighting since we care about conversations
    return (likes * 1.0) + (replies * 2.5) + (retweets * 0.8) + (quotes * 1.5)


def _icp_relevance(text: str) -> float:
    body = text.lower()
    pos = sum(1 for token in ICP_KEYWORDS if token in body)
    neg = sum(1 for token in LOW_SIGNAL_KEYWORDS if token in body)
    raw = (pos * 0.15) - (neg * 0.25) + 0.5
    return clamp(raw, 0.0, 1.0)


def _noise_penalty(text: str) -> float:
    body = text.strip()
    if not body:
        return 0.4
    if len(body) < 25:
        return 0.2
    if body.lower().startswith("rt @"):
        return 0.35
    if body.count("#") >= 5:
        return 0.2
    return 0.0


def _composite_score(text: str, metrics: Dict[str, Any]) -> float:
    engagement = _engagement_score(metrics)
    icp = _icp_relevance(text)
    penalty = _noise_penalty(text)
    return max(0.0, (engagement * (0.6 + icp)) - (engagement * penalty))


def run_research(
    x_client: XClient,
    queries: List[str],
    tracked_accounts: Dict[str, List[str]],
    out_dir: Path,
    max_per_query: int = 40,
) -> ResearchResult:
    run_id = utc_now_compact()
    rows: List[Dict[str, Any]] = []
    seen_tweet_ids = set()

    expanded_queries = list(queries)
    for tier in ["tier1", "tier2", "tier3"]:
        for handle in tracked_accounts.get(tier, []):
            expanded_queries.append(f"from:{str(handle).lstrip('@')} -is:retweet")

    for query in expanded_queries:
        payload = x_client.search_recent(query=query, max_results=max_per_query)
        users = {
            u.get("id"): u
            for u in (payload.get("includes", {}).get("users", []) or [])
            if u.get("id")
        }
        for tweet in payload.get("data", []) or []:
            tweet_id = tweet.get("id")
            if not tweet_id or tweet_id in seen_tweet_ids:
                continue
            seen_tweet_ids.add(tweet_id)
            metrics = tweet.get("public_metrics", {}) or {}
            text = tweet.get("text", "")
            author_id = tweet.get("author_id")
            author = users.get(author_id, {}) if author_id else {}
            row = {
                "tweet_id": tweet_id,
                "query": query,
                "text": text,
                "author_id": author_id,
                "username": author.get("username"),
                "created_at": tweet.get("created_at"),
                "metrics": {
                    "replies": metrics.get("reply_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "likes": metrics.get("like_count", 0),
                    "quotes": metrics.get("quote_count", 0),
                },
                "scores": {
                    "engagement": _engagement_score(metrics),
                    "icp_relevance": _icp_relevance(text),
                    "noise_penalty": _noise_penalty(text),
                    "composite": _composite_score(text, metrics),
                },
            }
            rows.append(row)

    rows.sort(key=lambda x: float(x["scores"]["composite"]), reverse=True)
    artifact_path = out_dir / f"research_{run_id}.json"
    write_json_file(artifact_path, {"run_id": run_id, "items": rows})
    return ResearchResult(run_id=run_id, items=rows, artifact_path=artifact_path)

