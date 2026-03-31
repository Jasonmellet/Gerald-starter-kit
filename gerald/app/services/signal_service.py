from __future__ import annotations

from pathlib import Path
from typing import List

from rich.console import Console

from ..clients.anthropic_client import AnthropicClient
from ..db import get_session
from ..logging import get_logger
from ..models import Prospect
from ..repositories import posts as posts_repo
from ..repositories import prospect_run_states as run_states_repo
from ..repositories import prospects as prospects_repo
from ..repositories import signals as signals_repo
from ..schemas import SignalExtract
from ..structured_output import (
    get_debug_dir,
    get_structured,
    repair_json_with_llm,
    StructuredOutputStats,
)

logger = get_logger(__name__)
console = Console()
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "signal_extraction.txt"

SIGNAL_SCHEMA_HINT = (
    "JSON array of objects: signal_type (one of HIRING_MARKETING, FOUNDER_DOING_GTM, etc.), "
    "confidence (0-1), signal_strength (0-1), evidence_text (string), "
    "extracted_pain_point, extracted_goal, rationale (optional strings). Empty array [] if no signals."
)


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def analyze_signals_for_all_prospects(limit: int | None = None) -> dict:
    """
    Extract signals for prospects with posts or bio. Returns summary with parse_successes, parse_failures, repaired.
    """
    anthropic_client = AnthropicClient()
    system_prompt = _load_prompt()
    debug_dir = get_debug_dir()

    def complete_fn(system: str, user_content: str) -> str:
        return anthropic_client.cheap_complete(system=system, user_content=user_content, max_tokens=1024)

    def repair_fn(raw: str) -> str:
        return repair_json_with_llm(raw, SIGNAL_SCHEMA_HINT, complete_fn)

    totals = {"parse_successes": 0, "parse_failures": 0, "repaired": 0, "validation_failures": 0}

    with get_session() as session:
        prospects: List[Prospect] = list(prospects_repo.list_all(session, limit=limit, min_icp_score=2.0))
        for prospect in prospects:
            posts = list(posts_repo.list_for_prospect(session, prospect.id))
            if not posts and not prospect.bio:
                continue

            context_chunks = []
            if prospect.bio:
                context_chunks.append(f"BIO:\n{prospect.bio}\n")
            if posts:
                texts = "\n\n".join(f"- {p.text}" for p in posts[:20])
                context_chunks.append(f"RECENT_POSTS:\n{texts}")
            context = "\n\n".join(context_chunks)

            try:
                raw = complete_fn(system_prompt, context)
            except Exception as exc:
                logger.error("Signal extraction failed", extra={"prospect_id": prospect.id, "error": str(exc)})
                totals["parse_failures"] += 1
                continue

            result, stats = get_structured(
                raw,
                schema_class=SignalExtract,
                expect_list=True,
                step_name="signal_extraction",
                debug_dir=debug_dir,
                repair_fn=repair_fn,
            )

            if stats.parse_failures:
                totals["parse_failures"] += 1
                if stats.raw_saved_path:
                    logger.debug("Signal raw saved", extra={"path": stats.raw_saved_path})
                continue
            if stats.validation_failures or not result:
                totals["validation_failures"] += 1
                continue
            if stats.repaired:
                totals["repaired"] += 1
            totals["parse_successes"] += 1

            for extract in result:
                signals_repo.create_from_extract(session, prospect.id, post_id=None, extract=extract)
            session.commit()

        logger.info("Signal analysis completed", extra=totals)

    return totals


def analyze_signals_for_run(session, run_id: int) -> dict:
    """Extract signals only for prospects in this run's batch. Marks analyzed on success."""
    anthropic_client = AnthropicClient()
    system_prompt = _load_prompt()
    debug_dir = get_debug_dir()

    def complete_fn(system: str, user_content: str) -> str:
        return anthropic_client.cheap_complete(system=system, user_content=user_content, max_tokens=1024)

    def repair_fn(raw: str) -> str:
        return repair_json_with_llm(raw, SIGNAL_SCHEMA_HINT, complete_fn)

    totals = {"parse_successes": 0, "parse_failures": 0, "repaired": 0, "validation_failures": 0}
    prospect_ids = run_states_repo.list_prospect_ids_for_run(session, run_id, only_discovered=True)

    for prospect_id in prospect_ids:
        prospect = session.get(Prospect, prospect_id)
        if not prospect:
            continue
        posts = list(posts_repo.list_for_prospect(session, prospect.id))
        if not posts and not prospect.bio:
            continue

        context_chunks = []
        if prospect.bio:
            context_chunks.append(f"BIO:\n{prospect.bio}\n")
        if posts:
            texts = "\n\n".join(f"- {p.text}" for p in posts[:20])
            context_chunks.append(f"RECENT_POSTS:\n{texts}")
        context = "\n\n".join(context_chunks)

        try:
            raw = complete_fn(system_prompt, context)
        except Exception as exc:
            logger.error("Signal extraction failed", extra={"prospect_id": prospect.id, "error": str(exc)})
            totals["parse_failures"] += 1
            continue

        result, stats = get_structured(
            raw,
            schema_class=SignalExtract,
            expect_list=True,
            step_name="signal_extraction",
            debug_dir=debug_dir,
            repair_fn=repair_fn,
        )

        if stats.parse_failures:
            totals["parse_failures"] += 1
            continue
        if stats.validation_failures or not result:
            totals["validation_failures"] += 1
            continue
        if stats.repaired:
            totals["repaired"] += 1
        totals["parse_successes"] += 1

        for extract in result:
            signals_repo.create_from_extract(session, prospect.id, post_id=None, extract=extract)
        run_states_repo.mark_analyzed(session, run_id, prospect.id)
        session.commit()

    logger.info("Signal analysis for run completed", extra={"run_id": run_id, **totals})
    return totals

