from __future__ import annotations

from pathlib import Path
from typing import List

from rich.console import Console

from ..clients.anthropic_client import AnthropicClient
from ..db import get_session
from ..logging import get_logger
from ..models import Opportunity, Prospect
from ..repositories import opportunities as opp_repo
from ..repositories import prospect_run_states as run_states_repo
from ..repositories import prospects as prospects_repo
from ..repositories import signals as signals_repo
from ..schemas import OpportunityScores
from ..structured_output import get_debug_dir, get_structured, repair_json_with_llm

logger = get_logger(__name__)
console = Console()
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "scoring_rationale.txt"
MIN_OPPORTUNITY_SCORE = 50

SCORING_SCHEMA_HINT = (
    "JSON object: urgency_score, fit_score, buyer_score, outreach_score, confidence_score (0-100), "
    "overall_score (optional), summary (string), why_now, recommended_angle (optional strings)."
)


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def is_outreach_qualified(opportunity: Opportunity) -> bool:
    """True if opportunity meets stricter criteria for generating outreach drafts."""
    overall = opportunity.overall_score or 0
    buyer = opportunity.buyer_score or 0
    confidence = opportunity.confidence_score or 0
    return overall >= 65 and buyer >= 60 and confidence >= 50


def score_opportunities(limit: int | None = None) -> dict:
    """
    Score prospects with signals and create/update opportunities. Returns summary with parse_successes, parse_failures, repaired.
    """
    anthropic_client = AnthropicClient()
    system_prompt = _load_prompt()
    debug_dir = get_debug_dir()

    def complete_fn(system: str, user_content: str) -> str:
        return anthropic_client.strong_complete(system=system, user_content=user_content, max_tokens=512)

    def repair_fn(raw: str) -> str:
        return repair_json_with_llm(raw, SCORING_SCHEMA_HINT, complete_fn)

    totals = {"parse_successes": 0, "parse_failures": 0, "repaired": 0, "validation_failures": 0}

    with get_session() as session:
        prospects: List[Prospect] = list(prospects_repo.list_all(session, limit=limit))

        for prospect in prospects:
            signals = list(signals_repo.list_for_prospect(session, prospect.id))
            if not signals:
                continue

            context_parts: List[str] = []
            context_parts.append(
                f"PROSPECT:\nhandle={prospect.handle}, "
                f"display_name={prospect.display_name}, "
                f"role_guess={prospect.role_guess}, "
                f"company_guess={prospect.company_guess}\n"
            )
            if prospect.fit_notes:
                context_parts.append(f"FIT_NOTES:\n{prospect.fit_notes}\n")
            sig_lines = []
            for s in signals[:10]:
                sig_lines.append(
                    f"- type={s.signal_type}, conf={s.confidence:.2f}, " f"evidence={s.evidence_text}"
                )
            context_parts.append("SIGNALS:\n" + "\n".join(sig_lines))
            context = "\n\n".join(context_parts)

            try:
                raw = complete_fn(system_prompt, context)
            except Exception as exc:
                logger.error("Scoring failed", extra={"prospect_id": prospect.id, "error": str(exc)})
                totals["parse_failures"] += 1
                continue

            result, stats = get_structured(
                raw,
                schema_class=OpportunityScores,
                expect_list=False,
                step_name="scoring",
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

            scores = result
            if (scores.overall_score or 0) < MIN_OPPORTUNITY_SCORE:
                prospect.prospect_status = "low_priority"
                session.commit()
                continue
            opp = opp_repo.get_or_create_for_prospect(session, prospect.id)
            opp_repo.apply_scores(opp, scores)
            session.commit()

        logger.info("Scoring completed", extra=totals)

    return totals


def score_opportunities_for_run(session, run_id: int) -> dict:
    """Score only prospects in this run's batch (analyzed). Create/update Opportunity, mark_scored."""
    anthropic_client = AnthropicClient()
    system_prompt = _load_prompt()
    debug_dir = get_debug_dir()

    def complete_fn(system: str, user_content: str) -> str:
        return anthropic_client.strong_complete(system=system, user_content=user_content, max_tokens=512)

    def repair_fn(raw: str) -> str:
        return repair_json_with_llm(raw, SCORING_SCHEMA_HINT, complete_fn)

    totals = {"parse_successes": 0, "parse_failures": 0, "repaired": 0, "validation_failures": 0}
    prospect_ids = run_states_repo.list_prospect_ids_for_run(
        session, run_id, only_discovered=True, only_analyzed=True
    )

    for prospect_id in prospect_ids:
        prospect = session.get(Prospect, prospect_id)
        if not prospect:
            continue
        signals = list(signals_repo.list_for_prospect(session, prospect.id))
        if not signals:
            continue

        context_parts = [
            f"PROSPECT:\nhandle={prospect.handle}, "
            f"display_name={prospect.display_name}, "
            f"role_guess={prospect.role_guess}, "
            f"company_guess={prospect.company_guess}\n",
        ]
        if prospect.fit_notes:
            context_parts.append(f"FIT_NOTES:\n{prospect.fit_notes}\n")
        sig_lines = [
            f"- type={s.signal_type}, conf={s.confidence:.2f}, evidence={s.evidence_text}"
            for s in signals[:10]
        ]
        context_parts.append("SIGNALS:\n" + "\n".join(sig_lines))
        context = "\n\n".join(context_parts)

        try:
            raw = complete_fn(system_prompt, context)
        except Exception as exc:
            logger.error("Scoring failed", extra={"prospect_id": prospect.id, "error": str(exc)})
            totals["parse_failures"] += 1
            continue

        result, stats = get_structured(
            raw,
            schema_class=OpportunityScores,
            expect_list=False,
            step_name="scoring",
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

        scores = result
        if (scores.overall_score or 0) < MIN_OPPORTUNITY_SCORE:
            prospect.prospect_status = "low_priority"
            session.commit()
            continue
        opp = opp_repo.get_or_create_for_prospect(session, prospect.id)
        opp_repo.apply_scores(opp, scores)
        run_states_repo.mark_scored(session, run_id, prospect.id)
        session.commit()

    logger.info("Scoring for run completed", extra={"run_id": run_id, **totals})
    return totals

