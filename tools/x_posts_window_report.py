#!/usr/bin/env python3
"""
Fetch all posts for an account in a recent time window (default 7 days) via X API v2.

Uses app bearer token (X_BEARER_TOKEN) like tools/x_api_client.py.
Resolves account by:
  1) --username @handle or handle
  2) env X_ACCOUNT_USERNAME
  3) numeric user id prefix from X_ACCESS_TOKEN (OAuth1 format "<id>-...")

Writes JSON + Markdown summary under outputs/ and prints a short table to stdout.

Usage:
  python3 tools/x_posts_window_report.py
  python3 tools/x_posts_window_report.py --days 7 --username yourhandle
  python3 tools/x_posts_window_report.py --days 7 --no-md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"

# Substrings that match recurring x_system / GTM template posts (for the weekly review section).
PIPELINE_STYLE_MARKERS: tuple[str, ...] = (
    "The pipeline problem usually starts earlier",
    "Vibe coding lets founders",
    "A surprising number of SMB",
    "PPC clicks going up while conversions stay flat",
    "A lot of growth stalls start with one ownership gap",
    "Most SMBs do not have a lead problem",
    "Paid leads sit",
    "Growth feels random and non-repeatable",
)


def load_env() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ.setdefault(key, val)


def api_get_bearer(endpoint: str, params: Dict[str, Any], bearer: str) -> Dict[str, Any]:
    import urllib.error
    import urllib.request

    url = f"https://api.x.com/2{endpoint}"
    if params:
        url += "?" + urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer}",
            "User-Agent": "OpenClawXPostsWindow/0.1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise SystemExit(f"HTTP {e.code}: {body}") from e


def resolve_user_id(
    bearer: str,
    username: Optional[str],
) -> tuple[str, Optional[str]]:
    """Return (user_id, username_for_display)."""
    if username:
        u = username.lstrip("@").strip()
        data = api_get_bearer(f"/users/by/username/{u}", {"user.fields": "username,name"}, bearer)
        if "data" not in data:
            raise SystemExit(f"User not found: {u!r} — {data}")
        uid = data["data"]["id"]
        return uid, data["data"].get("username", u)

    env_u = (os.environ.get("X_ACCOUNT_USERNAME") or os.environ.get("TWITTER_USERNAME") or "").strip()
    if env_u:
        return resolve_user_id(bearer, env_u)

    token = os.environ.get("X_ACCESS_TOKEN") or os.environ.get("x_access_token") or ""
    prefix = token.split("-", 1)[0] if token else ""
    if prefix.isdigit():
        data = api_get_bearer(f"/users/{prefix}", {"user.fields": "username,name"}, bearer)
        if "data" not in data:
            raise SystemExit(
                f"Could not load user id {prefix} from token prefix. "
                "Pass --username or set X_ACCOUNT_USERNAME in .env"
            )
        return prefix, data["data"].get("username")

    raise SystemExit(
        "Set --username, or X_ACCOUNT_USERNAME in .env, or X_ACCESS_TOKEN with form '<user_id>-...'"
    )


def fetch_timeline_window(
    bearer: str,
    user_id: str,
    start_time_iso: str,
    max_pages: int = 50,
) -> List[Dict[str, Any]]:
    """Paginate GET /2/users/:id/tweets until no next_token or max_pages."""
    all_rows: List[Dict[str, Any]] = []
    token: Optional[str] = None
    for _ in range(max_pages):
        params: Dict[str, Any] = {
            "max_results": 100,
            "tweet.fields": "created_at,public_metrics,conversation_id,in_reply_to_user_id",
            "start_time": start_time_iso,
        }
        if token:
            params["pagination_token"] = token
        data = api_get_bearer(f"/users/{user_id}/tweets", params, bearer)
        batch = data.get("data") or []
        all_rows.extend(batch)
        meta = data.get("meta") or {}
        token = meta.get("next_token")
        if not token:
            break
    return all_rows


def _is_retweet(t: Dict[str, Any]) -> bool:
    text = (t.get("text") or "").lstrip()
    return text.startswith("RT @")


def _engagement_score(t: Dict[str, Any]) -> int:
    m = t.get("public_metrics") or {}
    return int(m.get("like_count", 0) or 0)


def _tweet_url(tweet_id: str, username: Optional[str]) -> str:
    return f"https://x.com/i/status/{tweet_id}"


def build_markdown_report(
    summary: Dict[str, Any],
    tweets: List[Dict[str, Any]],
) -> str:
    """Human-readable weekly-style summary (Markdown)."""
    uname = summary.get("username") or "account"
    days = summary.get("window_days", 7)
    start = summary.get("start_time_utc", "")
    gen = summary.get("generated_at", "")
    lines: List[str] = [
        f"# X posts — last {days} days",
        "",
        f"- **Account:** @{uname}",
        f"- **Window (UTC):** from `{start}` through report time",
        f"- **Generated:** `{gen}`",
        f"- **Total tweets in window:** {len(tweets)}",
        "",
        "Note: For **retweets**, `public_metrics` often reflect the *original* tweet, not your RT.",
        "",
        "## Totals by type",
        "",
    ]

    originals: List[Dict[str, Any]] = []
    replies: List[Dict[str, Any]] = []
    rts: List[Dict[str, Any]] = []
    for t in tweets:
        if _is_retweet(t):
            rts.append(t)
        elif t.get("in_reply_to_user_id"):
            replies.append(t)
        else:
            originals.append(t)

    lines.append(f"| Type | Count |")
    lines.append(f"|------|-------|")
    lines.append(f"| Original posts | {len(originals)} |")
    lines.append(f"| Replies | {len(replies)} |")
    lines.append(f"| Retweets | {len(rts)} |")
    lines.append("")

    total_likes = sum(_engagement_score(t) for t in tweets)
    lines.append(f"- **Sum of like_count (all rows):** {total_likes}")
    lines.append("")

    # Template-style posts
    template_hits: List[Dict[str, Any]] = []
    for t in tweets:
        if _is_retweet(t) or t.get("in_reply_to_user_id"):
            continue
        text = t.get("text") or ""
        if any(m in text for m in PIPELINE_STYLE_MARKERS):
            template_hits.append(t)

    lines.append("## Pipeline / template-style originals")
    lines.append("")
    if not template_hits:
        lines.append("*No originals matched the configured template markers.*")
    else:
        lines.append(f"*{len(template_hits)} post(s) matched heuristic markers (see `PIPELINE_STYLE_MARKERS` in script).*")
        lines.append("")
        for t in sorted(template_hits, key=lambda x: x.get("created_at") or ""):
            tid = t.get("id", "")
            m = t.get("public_metrics") or {}
            preview = (t.get("text") or "").replace("\n", " ").strip()[:160]
            lines.append(f"- `{tid}` — ♥{m.get('like_count', 0)} 🔁{m.get('retweet_count', 0)} 💬{m.get('reply_count', 0)} — [{preview}…]({_tweet_url(str(tid), uname)})")
    lines.append("")

    # Top 5 by likes (all)
    lines.append("## Top 5 by likes (all types)")
    lines.append("")
    sorted_all = sorted(tweets, key=_engagement_score, reverse=True)[:5]
    for i, t in enumerate(sorted_all, 1):
        tid = str(t.get("id", ""))
        m = t.get("public_metrics") or {}
        kind = "RT" if _is_retweet(t) else ("reply" if t.get("in_reply_to_user_id") else "post")
        preview = (t.get("text") or "").replace("\n", " ").strip()[:120]
        lines.append(f"{i}. **{kind}** ♥{m.get('like_count', 0)} — [{preview}…]({_tweet_url(tid, uname)})")
    lines.append("")

    # Top 5 originals only (exclude RT and replies) — clearer for "your posts"
    lines.append("## Top 5 originals only (not replies, not RTs)")
    lines.append("")
    sorted_orig = sorted(originals, key=_engagement_score, reverse=True)[:5]
    if not sorted_orig:
        lines.append("*No original posts in window.*")
    else:
        for i, t in enumerate(sorted_orig, 1):
            tid = str(t.get("id", ""))
            m = t.get("public_metrics") or {}
            preview = (t.get("text") or "").replace("\n", " ").strip()[:120]
            lines.append(f"{i}. ♥{m.get('like_count', 0)} 🔁{m.get('retweet_count', 0)} 💬{m.get('reply_count', 0)} — [{preview}…]({_tweet_url(tid, uname)})")
    lines.append("")

    lines.append("## Next step")
    lines.append("")
    lines.append("Fill in qualitative notes in `docs/x-weekly-content-review.md` (why it worked / pivot).")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="X posts in last N days (API v2)")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default 7)")
    parser.add_argument("--username", type=str, default=None, help="Account handle (optional if env/token)")
    parser.add_argument("--json-out", type=str, default=None, help="Override output JSON path")
    parser.add_argument("--md-out", type=str, default=None, help="Override output Markdown path")
    parser.add_argument("--no-md", action="store_true", help="Skip writing Markdown summary")
    args = parser.parse_args()

    bearer = os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        sys.exit("X_BEARER_TOKEN missing in environment / .env")

    user_id, uname = resolve_user_id(bearer, args.username)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=args.days)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")

    tweets = fetch_timeline_window(bearer, user_id, start_iso)
    # Client-side filter (API start_time should already bound; keep strict)
    cutoff = start
    filtered: List[Dict[str, Any]] = []
    for t in tweets:
        created_raw = t.get("created_at") or ""
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            created = None
        if created is None or created >= cutoff:
            filtered.append(t)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.json_out) if args.json_out else OUTPUT_DIR / f"x_posts_last_{args.days}d_{stamp}.json"

    summary = {
        "generated_at": now.isoformat(),
        "window_days": args.days,
        "start_time_utc": start_iso,
        "user_id": user_id,
        "username": uname,
        "tweet_count": len(filtered),
        "tweets": filtered,
    }
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_path: Optional[Path] = None
    if not args.no_md:
        md_path = Path(args.md_out) if args.md_out else out_path.with_suffix(".md")
        md_path.write_text(build_markdown_report(summary, filtered), encoding="utf-8")

    print(f"Account: @{uname or user_id} (id={user_id})")
    print(f"Window: last {args.days} days since {start_iso} (UTC)")
    print(f"Tweets in window: {len(filtered)}")
    print(f"Wrote: {out_path}")
    if md_path:
        print(f"Wrote: {md_path}")
    print()

    # Table: id, created, likes, RT, replies, preview
    def row_line(t: Dict[str, Any]) -> str:
        m = t.get("public_metrics") or {}
        text = (t.get("text") or "").replace("\n", " ")[:72]
        reply = "reply" if t.get("in_reply_to_user_id") else "post"
        return (
            f"{t.get('id')} | {reply:5} | {str(t.get('created_at', ''))[:19]}Z | "
            f"♥{m.get('like_count', 0)} 🔁{m.get('retweet_count', 0)} 💬{m.get('reply_count', 0)} | {text}"
        )

    for t in sorted(filtered, key=lambda x: x.get("created_at") or ""):
        print(row_line(t))

    if not filtered:
        print(
            "\n(No tweets returned — account may be quiet, or handle/token mismatch, "
            "or API tier limits timeline reads.)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
