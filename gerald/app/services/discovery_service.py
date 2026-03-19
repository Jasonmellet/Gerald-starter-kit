from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Dict

from rich.console import Console

from ..clients.x_client import XClient, XClientRateLimitError, XClientNotFoundError, XClientError
from ..config import get_settings
from ..constants import FOUNDER_KEYWORDS, NEGATIVE_PROFILE_KEYWORDS
from ..db import get_session
from ..logging import get_logger
from ..models import PipelineRun
from ..repositories import posts as posts_repo
from ..repositories import pipeline_runs as pipeline_runs_repo
from ..repositories import prospect_run_states as run_states_repo
from ..repositories import prospects as prospects_repo


logger = get_logger(__name__)
console = Console()

ICP_MIN_SCORE = 2

STARTUP_SAAS_KEYWORDS = ["startup", "saas", "b2b", "building", "build in public", "product"]

BRAND_ACCOUNT_PHRASES = ["official account", "brand account", "company account"]


def _is_likely_brand_account(bio: str, handle: str) -> bool:
    """True if the account appears to be a company/brand account rather than an individual."""
    lower_bio = (bio or "").lower()
    if any(phrase in lower_bio for phrase in BRAND_ACCOUNT_PHRASES):
        return True
    lower_handle = (handle or "").lower()
    if any(phrase in lower_handle for phrase in BRAND_ACCOUNT_PHRASES):
        return True
    return False


def _bio_contains_any(bio: str, keywords: List[str]) -> bool:
    lower = (bio or "").lower()
    return any(kw in lower for kw in keywords)


def compute_icp_score(bio: str, has_website: bool, follower_count: int) -> int:
    score = 0
    if _bio_contains_any(bio, FOUNDER_KEYWORDS):
        score += 3
    if _bio_contains_any(bio, STARTUP_SAAS_KEYWORDS):
        score += 2
    if has_website:
        score += 2
    else:
        score -= 1
    if follower_count > 200:
        score += 1
    if _bio_contains_any(bio, NEGATIVE_PROFILE_KEYWORDS):
        score -= 3
    return score


def _build_discovery_reason(
    query: str,
    bio: str,
    has_website: bool,
    follower_count: int,
    icp_score: int,
) -> str:
    parts = [f"Matched query '{query}'"]
    found = [kw for kw in FOUNDER_KEYWORDS if kw in (bio or "").lower()]
    if found:
        parts.append(f"bio contains '{found[0]}'")
    if has_website:
        parts.append("website present")
    else:
        parts.append("no website")
    if follower_count > 200:
        parts.append("followers > 200")
    parts.append(f"icp_score={icp_score}")
    return "; ".join(parts)


def run_discovery_for_run(session, run: PipelineRun) -> int:
    """
    Run discovery for a pipeline run: use run's window (discovery_window_start/end) and limit.
    Add each accepted prospect to ProspectRunState for this run. Return discovered_count.
    """
    settings = get_settings()
    x_client = XClient()
    queries = list(settings.discovery_queries)
    window_start = run.discovery_window_start
    window_end = run.discovery_window_end
    if getattr(window_start, "tzinfo", None) is None:
        window_start = window_start.replace(tzinfo=timezone.utc)
    if getattr(window_end, "tzinfo", None) is None:
        window_end = window_end.replace(tzinfo=timezone.utc)
    max_prospects = run.discovery_limit

    posts_fetched = 0
    prospects_added_to_run = 0
    prospects_skipped = 0
    seen_user_ids: set[str] = set()

    for query in queries:
        per_query_limit = min(50, max(15, max_prospects // len(queries)))
        try:
            result: Dict[str, object] = x_client.search_recent_posts(query, limit=per_query_limit)
            tweets = result.get("tweets", [])  # type: ignore[assignment]
            users_by_id = result.get("users_by_id", {})  # type: ignore[assignment]
            if not isinstance(tweets, list):
                tweets = []
            if not isinstance(users_by_id, dict):
                users_by_id = {}
        except XClientRateLimitError:
            continue
        except XClientError:
            continue

        for tweet in tweets:  # type: ignore[assignment]
            created_at = tweet.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    created_at_dt = window_end
            else:
                created_at_dt = created_at or window_end
            if getattr(created_at_dt, "tzinfo", None) is None:
                created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)

            if created_at_dt < window_start or created_at_dt > window_end:
                continue

            author_id = tweet.get("author_id")
            if not author_id:
                prospects_skipped += 1
                continue

            posts_fetched += 1
            existing = prospects_repo.get_by_x_user_id(session, author_id)

            if author_id in seen_user_ids:
                if existing:
                    run_states_repo.add_to_run(session, run.id, existing.id, included_in_discovery=True)
                    posts_repo.upsert_from_x_post(session, existing.id, tweet)
                session.commit()
                continue

            seen_user_ids.add(author_id)

            profile = users_by_id.get(author_id)
            if profile is None:
                try:
                    bulk = x_client.get_users_bulk([author_id])
                    profile = bulk[0] if bulk else None
                except (XClientRateLimitError, XClientNotFoundError, XClientError):
                    continue
            if not profile:
                profile = {
                    "id": author_id,
                    "username": author_id,
                    "name": author_id,
                    "description": "",
                    "location": None,
                    "public_metrics": {},
                    "url": None,
                }
            if not isinstance(profile, dict):
                continue

            bio = (profile.get("description") or "").strip()
            website = (profile.get("url") or "").strip()
            metrics = profile.get("public_metrics") or {}
            follower_count = int(metrics.get("followers_count") or 0)
            if follower_count < 20:
                continue
            if not bio and not website:
                continue
            if _bio_contains_any(bio, NEGATIVE_PROFILE_KEYWORDS):
                continue
            handle = (profile.get("username") or "").strip()
            if _is_likely_brand_account(bio, handle):
                continue
            icp_score = compute_icp_score(bio, bool(website), follower_count)
            if icp_score < ICP_MIN_SCORE:
                continue

            discovery_reason = _build_discovery_reason(query, bio, bool(website), follower_count, icp_score)
            prospect = prospects_repo.upsert_from_x_profile(session, profile)  # type: ignore[arg-type]
            prospect.icp_score = float(icp_score)
            prospect.discovery_reason = discovery_reason
            session.flush()
            posts_repo.upsert_from_x_post(session, prospect.id, tweet)
            run_states_repo.add_to_run(session, run.id, prospect.id, included_in_discovery=True)
            prospects_added_to_run += 1
            session.commit()

            if prospects_added_to_run >= max_prospects:
                break
        if prospects_added_to_run >= max_prospects:
            break

    discovered_count = run_states_repo.count_discovered_for_run(session, run.id)
    run.discovered_count = discovered_count
    pipeline_runs_repo.update_run_counts(session, run.id, discovered_count=discovered_count)
    logger.info("Run discovery completed", extra={"run_id": run.id, "discovered_count": discovered_count})
    return discovered_count


def run_discovery(
    queries: Iterable[str] | None = None,
    max_prospects: int | None = None,
):
    """
    Run discovery across a set of search queries and store prospects/posts.
    If max_prospects is set, stop after storing that many new prospects (for test runs).
    Returns dict with prospects_created.
    """

    settings = get_settings()
    x_client = XClient()
    queries = list(queries or settings.discovery_queries)

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.default_lookback_days)
    logger.info(
        "Starting discovery",
        extra={"queries": queries, "cutoff": cutoff.isoformat(), "max_prospects": max_prospects},
    )

    posts_fetched = 0
    prospects_created = 0
    prospects_skipped = 0
    profile_rl_skipped = 0
    profile_other_errors = 0
    rate_limit_hits = 0
    authors_from_search = 0
    prospects_skipped_negative_filters = 0
    prospects_rejected_icp = 0

    with get_session() as session:
        seen_user_ids: set[str] = set()

        for query in queries:
            per_query_limit = min(settings.default_max_prospects, 15)
            try:
                result: Dict[str, object] = x_client.search_recent_posts(query, limit=per_query_limit)
                tweets = result.get("tweets", [])  # type: ignore[assignment]
                users_by_id = result.get("users_by_id", {})  # type: ignore[assignment]
                if not isinstance(tweets, list):
                    tweets = []
                if not isinstance(users_by_id, dict):
                    users_by_id = {}
            except XClientRateLimitError as exc:
                rate_limit_hits += 1
                logger.warning("Search rate limited", extra={"query": query, "error": str(exc)})
                continue
            except XClientError as exc:
                logger.error("Search failed", extra={"query": query, "error": str(exc)})
                continue

            for tweet in tweets:  # type: ignore[assignment]
                created_at = tweet.get("created_at")
                # Let X client provide datetime if available; otherwise skip stale ones defensively
                if isinstance(created_at, str):
                    try:
                        created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    except ValueError:
                        created_at_dt = cutoff
                else:
                    created_at_dt = created_at or cutoff

                if created_at_dt < cutoff:
                    continue

                author_id = tweet.get("author_id")
                if not author_id:
                    prospects_skipped += 1
                    continue

                posts_fetched += 1

                if author_id in seen_user_ids:
                    # Still store the post if we already saw this user
                    existing = prospects_repo.get_by_x_user_id(session, author_id)
                    if existing:
                        posts_repo.upsert_from_x_post(session, existing.id, tweet)
                        session.commit()
                    continue
                seen_user_ids.add(author_id)
                authors_from_search += 1

                profile = users_by_id.get(author_id)

                if profile is None:
                    # Optional, low-volume enrichment call with graceful handling
                    try:
                        bulk = x_client.get_users_bulk([author_id])
                        profile = bulk[0] if bulk else None
                    except XClientRateLimitError:
                        profile_rl_skipped += 1
                        rate_limit_hits += 1
                    except XClientNotFoundError:
                        logger.warning("Profile not found (404)", extra={"author_id": author_id})
                        prospects_skipped += 1
                    except XClientError as exc:
                        profile_other_errors += 1
                        logger.error("Profile lookup failed", extra={"author_id": author_id, "error": str(exc)})

                if not profile:
                    profile = {
                        "id": author_id,
                        "username": author_id,
                        "name": author_id,
                        "description": "",
                        "location": None,
                        "public_metrics": {},
                        "url": None,
                    }
                if not isinstance(profile, dict):
                    prospects_skipped += 1
                    continue

                bio = (profile.get("description") or "").strip()
                website = (profile.get("url") or "").strip()
                metrics = profile.get("public_metrics") or {}
                follower_count = int(metrics.get("followers_count") or 0)

                # Junk filter: skip before saving
                if follower_count < 20:
                    prospects_skipped_negative_filters += 1
                    logger.debug(
                        "Skipped (low followers)",
                        extra={"author_id": author_id, "handle": profile.get("username"), "followers": follower_count},
                    )
                    continue
                if not bio and not website:
                    prospects_skipped_negative_filters += 1
                    logger.debug("Skipped (no bio and no website)", extra={"author_id": author_id})
                    continue
                if _bio_contains_any(bio, NEGATIVE_PROFILE_KEYWORDS):
                    prospects_skipped_negative_filters += 1
                    logger.debug("Skipped (negative keywords in bio)", extra={"author_id": author_id, "handle": profile.get("username")})
                    continue
                handle = (profile.get("username") or "").strip()
                if _is_likely_brand_account(bio, handle):
                    prospects_skipped_negative_filters += 1
                    logger.debug(
                        "Skipped (brand/official account)",
                        extra={"author_id": author_id, "handle": handle},
                    )
                    continue

                icp_score = compute_icp_score(bio, bool(website), follower_count)
                if icp_score < ICP_MIN_SCORE:
                    prospects_rejected_icp += 1
                    logger.debug(
                        "Rejected (ICP score < %s)",
                        ICP_MIN_SCORE,
                        extra={"author_id": author_id, "handle": profile.get("username"), "icp_score": icp_score},
                    )
                    continue

                discovery_reason = _build_discovery_reason(query, bio, bool(website), follower_count, icp_score)

                prospect = prospects_repo.upsert_from_x_profile(session, profile)  # type: ignore[arg-type]
                prospect.icp_score = float(icp_score)
                prospect.discovery_reason = discovery_reason
                session.flush()
                posts_repo.upsert_from_x_post(session, prospect.id, tweet)
                prospects_created += 1
                session.commit()

                if max_prospects is not None and prospects_created >= max_prospects:
                    break
            if max_prospects is not None and prospects_created >= max_prospects:
                break

    logger.info(
        "Discovery completed",
        extra={
            "prospects_seen": len(seen_user_ids),
            "posts_fetched": posts_fetched,
            "prospects_created": prospects_created,
            "prospects_skipped": prospects_skipped,
            "profile_rl_skipped": profile_rl_skipped,
            "profile_other_errors": profile_other_errors,
            "rate_limit_hits": rate_limit_hits,
            "authors_from_search": authors_from_search,
            "prospects_skipped_negative_filters": prospects_skipped_negative_filters,
            "prospects_rejected_icp": prospects_rejected_icp,
        },
    )

    console.print("[bold]Discovery summary:[/bold]")
    console.print(f"  posts scanned: {posts_fetched}")
    console.print(f"  prospects found (authors from search): {authors_from_search}")
    console.print(f"  prospects skipped (negative filters): {prospects_skipped_negative_filters}")
    console.print(f"  prospects rejected by ICP score: {prospects_rejected_icp}")
    console.print(f"  prospects accepted for analysis: {prospects_created}")

    if posts_fetched == 0 or prospects_created == 0:
        if rate_limit_hits:
            console.print(
                "[yellow]Discovery completed but X rate limits prevented storing any prospects."
                " Try again later or reduce query volume.[/yellow]"
            )
        else:
            console.print(
                "[yellow]Discovery completed but no prospects matched the current queries and lookback window.[/yellow]"
            )
    else:
        console.print(
            f"[green]Discovery stored {posts_fetched} post(s) and {prospects_created} prospect(s). "
            f"Prospects skipped: {prospects_skipped}, profile 429 skips: {profile_rl_skipped}.[/green]"
        )
    return {"prospects_created": prospects_created}
