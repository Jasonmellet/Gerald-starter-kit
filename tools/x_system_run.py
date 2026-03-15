#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from x_system.ai_helper import AIHelper
from x_system.config import (
    build_paths,
    ensure_directories,
    load_queries,
    load_system_config,
    load_tracked_accounts,
    write_json_file,
)
from x_system.dm_handler import handle_dms
from x_system.generator import generate_candidates
from x_system.logger import build_logger
from x_system.patterns import extract_patterns
from x_system.planner import build_opportunities
from x_system.publisher import publish_winner
from x_system.ranker import rank_candidates
from x_system.reply_classifier import classify_replies
from x_system.reply_handler import handle_public_replies
from x_system.reply_monitor import monitor_replies
from x_system.research import run_research
from x_system.state_manager import StateManager, utc_now_iso
from x_system.x_client import XClient


def _send_failure_alert(reason: str, mode: str, cfg: Dict[str, Any]) -> None:
    """Send email notification on pipeline failure. Best-effort; does not raise."""
    to = (cfg or {}).get("alert_email", "jason@allgreatthings.io")
    if not to:
        return
    repo_root = Path(__file__).resolve().parent.parent
    send_script = repo_root / "tools" / "send_email.py"
    if not send_script.exists():
        return
    subject = f"X automation failed: {mode}"
    body = f"The X automation pipeline failed during mode '{mode}'.\n\nReason:\n{reason}\n\nCheck logs: {repo_root}/tools/x_system_logs/"
    try:
        subprocess.run(
            [sys.executable, str(send_script), "--to", to, "--subject", subject, "--body", body],
            cwd=str(repo_root),
            timeout=30,
            capture_output=True,
        )
    except Exception:
        pass


def _latest_artifact(path: Path, prefix: str) -> Optional[Path]:
    files = sorted(path.glob(f"{prefix}_*.json"))
    return files[-1] if files else None


def _load_artifact(path: Optional[Path]) -> Dict[str, Any]:
    if not path or not path.exists():
        return {}
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _log_stage(state: StateManager, stage: str, extra: Optional[Dict[str, Any]] = None) -> None:
    data = state.load_pipeline_state()
    data["stage"] = stage
    if extra:
        data.update(extra)
    state.save_pipeline_state(data)


def run_research_mode(client: XClient, paths, cfg: Dict[str, Any], logger) -> Dict[str, Any]:
    queries = load_queries(paths)
    tracked = load_tracked_accounts(paths)
    result = run_research(client, queries, tracked, paths.data_dir / "research", max_per_query=cfg.get("max_per_query", 40))
    logger.info(f"[research] wrote {result.artifact_path} with {len(result.items)} items")
    return {"research_path": str(result.artifact_path), "research_run_id": result.run_id}


def run_draft_mode(paths, state: StateManager, cfg: Dict[str, Any], logger, ai: AIHelper) -> Dict[str, Any]:
    research_artifact = _latest_artifact(paths.data_dir / "research", "research")
    research_data = _load_artifact(research_artifact)
    items: List[Dict[str, Any]] = research_data.get("items", [])
    if not items:
        raise RuntimeError("No research items found. Run research mode first.")

    patterns = extract_patterns(items, paths.data_dir / "decisions", top_n=cfg.get("pattern_top_n", 40))
    logger.info(f"[draft] wrote pattern summary {patterns.artifact_path}")

    theme_rotation = cfg.get("theme_rotation") or [
        "seo", "ai_ops", "vibe_coding", "ppc", "revops", "sales_systems", "agency_performance"
    ]
    pipeline = state.load_pipeline_state()
    last_idx = int(pipeline.get("last_theme_index", 0))
    primary_theme = theme_rotation[last_idx % len(theme_rotation)]
    pipeline["last_theme_index"] = (last_idx + 1) % len(theme_rotation)
    state.save_pipeline_state(pipeline)
    logger.info(f"[draft] theme for this run: {primary_theme} (next run: {theme_rotation[pipeline['last_theme_index'] % len(theme_rotation)]})")

    plan = build_opportunities(patterns.summary, paths.data_dir / "decisions", primary_theme=primary_theme)
    logger.info(f"[draft] wrote opportunities {plan.artifact_path}")
    candidates = generate_candidates(
        plan.opportunities,
        paths.data_dir / "posts",
        ai_helper=ai,
        max_candidates=int(cfg.get("candidate_batch_size", 10)),
        min_total_score=int(cfg.get("min_total_score", 35)),
        content_intel_enabled=bool(cfg.get("content_intel_enabled", True)),
        research_items=items,
    )
    logger.info(f"[draft] wrote candidates {candidates.artifact_path}")
    ranked = rank_candidates(
        candidates.candidates,
        paths.data_dir / "decisions",
        cfg.get(
            "scoring_weights",
            {
                "icp_match": 0.35,
                "opinion_strength": 0.2,
                "clarity": 0.15,
                "pain_relevance": 0.15,
                "reply_likelihood": 0.15,
            },
        ),
        min_total_score=int(cfg.get("min_total_score", 35)),
    )
    logger.info(f"[draft] winner candidate_id={ranked.winner.get('candidate_id')} score={ranked.winner.get('rank_score')}")
    return {
        "patterns_path": str(patterns.artifact_path),
        "plan_path": str(plan.artifact_path),
        "candidates_path": str(candidates.artifact_path),
        "ranked_path": str(ranked.artifact_path),
        "winner": ranked.winner,
    }


def _normalize_text_for_dedup(t: str) -> str:
    """Collapse whitespace and strip for duplicate check."""
    return " ".join((t or "").strip().split())


def _text_is_duplicate_of_recent(candidate_text: str, recent_texts: List[str], prefix_chars: int = 80) -> bool:
    """True if candidate matches any recent post (exact after normalize, or same opening)."""
    norm_c = _normalize_text_for_dedup(candidate_text)
    if not norm_c:
        return True
    prefix_c = norm_c[:prefix_chars]
    for r in recent_texts:
        norm_r = _normalize_text_for_dedup(r)
        if norm_c == norm_r or (len(norm_r) >= prefix_chars and norm_c[:prefix_chars] == norm_r[:prefix_chars]):
            return True
        if prefix_c and norm_r.startswith(prefix_c):
            return True
    return False


def run_publish_mode(client: XClient, paths, state: StateManager, cfg: Dict[str, Any], logger, dry_run: bool) -> Dict[str, Any]:
    ranked_artifact = _latest_artifact(paths.data_dir / "decisions", "ranked")
    ranked_data = _load_artifact(ranked_artifact)
    ranked_list = ranked_data.get("ranked", [])
    winner = ranked_data.get("winner")

    if not ranked_list:
        raise RuntimeError("No ranked candidates found. Run draft mode first.")

    # Avoid reposting the same or near-identical content (e.g. last post had zero interactions)
    posts_state = state.load_posts()
    recent_texts: List[str] = []
    for pid, rec in (posts_state.get("posts") or {}).items():
        if rec.get("dry_run"):
            continue
        t = rec.get("text")
        if t:
            recent_texts.append(t)
    # Keep last N to compare against (e.g. last 5 real posts)
    recent_texts = recent_texts[-5:]

    start_index = int(cfg.get("publish_top_n_index", 0))
    if start_index < 0:
        start_index = 0
    chosen = None
    for c in ranked_list[start_index:]:
        if not _text_is_duplicate_of_recent(c.get("text", ""), recent_texts):
            chosen = c
            break
    if chosen is None:
        logger.warning(
            "[publish] all candidates duplicate or too similar to recent posts; skipping publish to avoid reposting"
        )
        return {"post_id": None, "skipped_duplicate": True, "reason": "all candidates too similar to recent posts"}

    winner = chosen
    result = publish_winner(client, winner, paths.data_dir / "posts", dry_run=dry_run)
    logger.info(f"[publish] post_id={result.post_id} dry_run={dry_run}")
    state.record_post(
        result.post_id,
        {
            "post_id": result.post_id,
            "text": result.posted_text,
            "published_at": utc_now_iso(),
            "topic": winner.get("topic"),
            "winner": winner,
            "dry_run": dry_run,
        },
    )
    return {"post_id": result.post_id, "publish_path": str(result.artifact_path)}


def run_monitor_mode(
    client: XClient,
    paths,
    state: StateManager,
    cfg: Dict[str, Any],
    logger,
    dry_run: bool,
    post_id: Optional[str],
    ai: AIHelper,
) -> Dict[str, Any]:
    posts_state = state.load_posts()
    target_post_id = post_id or posts_state.get("latest_post_id")
    if not target_post_id and not posts_state.get("posts"):
        raise RuntimeError("No post_id available. Publish first or pass --post-id.")

    monitor_cfg = cfg.get("monitor", {})
    poll = int(monitor_cfg.get("poll_interval_seconds", 600))
    window = int(monitor_cfg.get("max_window_seconds", 0))
    lookback_hours = int(monitor_cfg.get("recent_post_lookback_hours", 48))
    max_posts = int(monitor_cfg.get("max_posts_per_monitor_run", 6))

    target_post_ids: List[str] = []
    if target_post_id:
        target_post_ids = [target_post_id]
    else:
        posts = list((posts_state.get("posts") or {}).values())
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        recent_ids: List[str] = []
        for p in posts:
            pid = p.get("post_id")
            published_at = p.get("published_at")
            if not pid or not published_at:
                continue
            try:
                dt = datetime.fromisoformat(str(published_at))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if dt >= cutoff:
                recent_ids.append(str(pid))
        target_post_ids = list(dict.fromkeys(recent_ids))[-max_posts:]

    all_classified_items: List[Dict[str, Any]] = []
    monitor_artifacts: List[str] = []
    for pid in target_post_ids:
        post_author_id: Optional[str] = None
        try:
            post_payload = client.get_tweet(str(pid))
            post_author_id = str((post_payload.get("data") or {}).get("author_id") or "") or None
        except Exception as exc:
            logger.warning(f"[monitor] unable to resolve post author for {pid}: {exc}")

        monitor = monitor_replies(
            client,
            pid,
            paths.data_dir / "replies",
            dry_run=dry_run,
            poll_interval_seconds=poll,
            max_window_seconds=window,
        )
        filtered_replies = monitor.replies
        if post_author_id:
            filtered_replies = [
                r for r in monitor.replies if str(r.get("author_id") or "") != post_author_id
            ]
            if len(filtered_replies) != len(monitor.replies):
                logger.info(
                    f"[monitor] filtered {len(monitor.replies) - len(filtered_replies)} self-authored replies for post_id={pid}"
                )
        monitor_artifacts.append(str(monitor.artifact_path))
        logger.info(f"[monitor] collected {len(filtered_replies)} replies for post_id={pid}")
        classified = classify_replies(filtered_replies, paths.data_dir / "decisions", ai_helper=ai)
        tagged = []
        for item in classified.items:
            row = dict(item)
            row["source_post_id"] = pid
            tagged.append(row)
        all_classified_items.extend(tagged)

    logger.info(f"[monitor] classified {len(all_classified_items)} replies across {len(target_post_ids)} posts")

    reply_actions = handle_public_replies(client, all_classified_items, state, paths.data_dir / "replies", dry_run=dry_run)
    logger.info(f"[monitor] reply actions={len(reply_actions.actions)}")

    dm_action_paths: List[str] = []
    dm_actions_total = 0
    for pid in target_post_ids:
        subset = [i for i in all_classified_items if i.get("source_post_id") == pid]
        dm_actions = handle_dms(client, subset, state, campaign_id=pid, out_dir=paths.data_dir / "decisions", dry_run=dry_run)
        dm_action_paths.append(str(dm_actions.artifact_path))
        dm_actions_total += len(dm_actions.actions)
    logger.info(f"[monitor] dm actions={dm_actions_total}")

    return {
        "post_ids": target_post_ids,
        "monitor_paths": monitor_artifacts,
        "classified_count": len(all_classified_items),
        "reply_actions_path": str(reply_actions.artifact_path),
        "dm_actions_paths": dm_action_paths,
    }


def run_full(
    client: XClient,
    paths,
    state: StateManager,
    cfg: Dict[str, Any],
    logger,
    dry_run: bool,
    ai: AIHelper,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    _log_stage(state, "research")
    out.update(run_research_mode(client, paths, cfg, logger))
    _log_stage(state, "draft")
    out.update(run_draft_mode(paths, state, cfg, logger, ai))
    _log_stage(state, "publish")
    out.update(run_publish_mode(client, paths, state, cfg, logger, dry_run))
    _log_stage(state, "monitor")
    out.update(run_monitor_mode(client, paths, state, cfg, logger, dry_run, post_id=out.get("post_id"), ai=ai))
    _log_stage(state, "complete", {"last_run_id": out.get("post_id")})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Local X automation system")
    parser.add_argument("mode", choices=["research", "draft", "publish", "monitor", "full"])
    parser.add_argument("--dry-run", action="store_true", help="Simulate writes without posting/replying/DMing")
    parser.add_argument("--post-id", default=None, help="Target post ID for monitor mode")
    args = parser.parse_args()

    paths = build_paths()
    ensure_directories(paths)
    cfg = load_system_config(paths)
    logger = build_logger(paths.logs_dir / "pipeline.log")
    state = StateManager(paths.state_dir)
    client = XClient()
    ai = AIHelper(enabled=bool(cfg.get("ai_enabled", False)))

    logger.info(f"[start] mode={args.mode} dry_run={args.dry_run}")
    _log_stage(state, "starting", {"requested_mode": args.mode})
    output: Dict[str, Any] = {}

    try:
        if args.mode == "research":
            output = run_research_mode(client, paths, cfg, logger)
        elif args.mode == "draft":
            output = run_draft_mode(paths, state, cfg, logger, ai)
        elif args.mode == "publish":
            output = run_publish_mode(client, paths, state, cfg, logger, args.dry_run)
        elif args.mode == "monitor":
            output = run_monitor_mode(client, paths, state, cfg, logger, args.dry_run, args.post_id, ai)
        elif args.mode == "full":
            output = run_full(client, paths, state, cfg, logger, args.dry_run, ai)

        learning_path = paths.data_dir / "learning" / f"run_{utc_now_iso().replace(':', '-')}.json"
        write_json_file(
            learning_path,
            {
                "mode": args.mode,
                "dry_run": args.dry_run,
                "output": output,
                "timestamp": utc_now_iso(),
            },
        )
        logger.info(f"[done] mode={args.mode} output_saved={learning_path}")
    except Exception as e:
        reason = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        logger.exception(f"[failed] mode={args.mode}")
        _send_failure_alert(reason, args.mode, cfg)
        raise


if __name__ == "__main__":
    main()

