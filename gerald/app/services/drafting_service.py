from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..clients.anthropic_client import AnthropicClient
from ..constants import DraftChannel
from ..db import get_session
from ..logging import get_logger
from ..models import Opportunity
from ..repositories import contact_history as contact_history_repo
from ..repositories import drafts as drafts_repo
from ..repositories import opportunities as opp_repo
from ..repositories import prospect_run_states as run_states_repo
from ..repositories import prospects as prospects_repo
from ..repositories import signals as signals_repo
from ..schemas import DraftOutput
from ..services.scoring_service import is_outreach_qualified
from ..structured_output import get_debug_dir, get_structured, repair_json_with_llm


logger = get_logger(__name__)

DM_BATCH_SIZE = 5

DRAFT_SINGLE_HINT = (
    "JSON object: channel 'dm', message_type (string), body (string), "
    "personalization_notes, cta, recommended_angle (optional strings)."
)
DRAFT_BATCH_HINT = (
    "JSON array of objects; each object: channel 'dm', message_type, body, "
    "personalization_notes, cta, recommended_angle. Same order as the numbered opportunities."
)
DM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "outreach_dm.txt"


def _load_dm_prompt() -> str:
    return DM_PROMPT_PATH.read_text(encoding="utf-8")


def _build_context(prospect, opportunity, signals) -> str:
    lines: List[str] = []
    lines.append(
        f"PROSPECT:\nhandle={prospect.handle}, display_name={prospect.display_name}, "
        f"role_guess={prospect.role_guess}, company_guess={prospect.company_guess}\n"
    )
    if opportunity.summary:
        lines.append(f"OPPORTUNITY_SUMMARY:\n{opportunity.summary}\n")
    if opportunity.why_now:
        lines.append(f"WHY_NOW:\n{opportunity.why_now}\n")
    if opportunity.recommended_angle:
        lines.append(f"RECOMMENDED_ANGLE:\n{opportunity.recommended_angle}\n")
    if signals:
        sig_lines = []
        for s in signals[:5]:
            sig_lines.append(
                f"- type={s.signal_type}, conf={s.confidence:.2f}, "
                f"evidence={s.evidence_text}"
            )
        lines.append("KEY_SIGNALS:\n" + "\n".join(sig_lines))
    return "\n\n".join(lines)


def _build_batch_context(opp_contexts: List[Tuple[object, object, List, str]]) -> str:
    """Build one user message for N opportunities. opp_contexts: list of (prospect, opp, signals, context_str)."""
    parts = [
        f"Draft DMs for the following {len(opp_contexts)} opportunities. "
        "Return a JSON array of exactly N objects in the same order. "
        "Each object: channel 'dm', message_type, body, personalization_notes, cta, recommended_angle.",
        "",
    ]
    for i, (_, _, _, ctx) in enumerate(opp_contexts, 1):
        parts.append(f"--- OPPORTUNITY {i} ---")
        parts.append(ctx)
        parts.append("")
    return "\n".join(parts).strip()


DM_MAX_CHARS = 320


def shorten_draft_body(session: Session, draft, max_chars: int = DM_MAX_CHARS) -> Optional[str]:
    """
    If the draft body exceeds max_chars, use the LLM to shorten it. Updates the draft in DB and returns the new body.
    Returns None if already short enough (no change) or if shortening fails.
    """
    body = (draft.body or "").strip()
    if len(body) <= max_chars:
        return body
    try:
        client = AnthropicClient()
        prompt = (
            f"Shorten this direct message to at most {max_chars} characters. "
            "Keep the same intent and tone. Return only the shortened message, no quotes or explanation.\n\n"
            f"Message:\n{body}"
        )
        out = client.performance_complete(
            system="You shorten messages to fit a character limit. Output only the shortened text.",
            user_content=prompt,
            max_tokens=400,
        )
        shortened = (out or "").strip().strip('"').strip("'")
        if not shortened or len(shortened) > max_chars:
            return None
        draft.body = shortened
        session.flush()
        return shortened
    except Exception as e:
        logger.warning("Draft shorten failed", extra={"draft_id": getattr(draft, "id", None), "error": str(e)})
        return None


def draft_for_top_opportunities(limit: int = 20) -> int:
    """Draft DMs only for outreach-qualified opportunities. Returns number of drafts created."""
    anthropic_client = AnthropicClient()
    dm_system = _load_dm_prompt()
    debug_dir = get_debug_dir()
    drafts_created = 0

    def complete_fn(system: str, user_content: str, max_tokens: int = 512) -> str:
        return anthropic_client.performance_complete(system=system, user_content=user_content, max_tokens=max_tokens)

    def repair_single_fn(raw: str) -> str:
        return repair_json_with_llm(raw, DRAFT_SINGLE_HINT, lambda s, u: complete_fn(s, u, max_tokens=1024))

    def repair_batch_fn(raw: str) -> str:
        return repair_json_with_llm(raw, DRAFT_BATCH_HINT, lambda s, u: complete_fn(s, u, max_tokens=2048))

    with get_session() as session:
        top_opps: List[Opportunity] = list(opp_repo.list_top_new(session, limit=limit))
        eligible: List[Tuple[Opportunity, object, List, str]] = []
        for opp in top_opps:
            if not is_outreach_qualified(opp):
                continue
            prospect = prospects_repo.get_by_x_user_id(session, opp.prospect.x_user_id) if opp.prospect else None
            prospect = prospect or opp.prospect
            if not prospect:
                continue
            if contact_history_repo.recently_contacted(session, prospect.id, within_days=30):
                continue
            signals = list(signals_repo.list_for_prospect(session, prospect.id))
            context = _build_context(prospect, opp, signals)
            eligible.append((opp, prospect, signals, context))

        # Process in batches of DM_BATCH_SIZE (one API call per batch)
        for i in range(0, len(eligible), DM_BATCH_SIZE):
            chunk = eligible[i : i + DM_BATCH_SIZE]
            batch_context = _build_batch_context(chunk)
            dm_raw = complete_fn(dm_system, batch_context, max_tokens=512 * len(chunk))
            dm_list, _ = get_structured(
                dm_raw,
                schema_class=DraftOutput,
                expect_list=True,
                step_name="draft_dm_batch",
                debug_dir=debug_dir,
                repair_fn=repair_batch_fn,
            )
            if not dm_list:
                for opp, _, _, _ in chunk:
                    logger.error("DM drafting failed", extra={"opportunity_id": opp.id})
                continue
            for j, (opp, _, _, _) in enumerate(chunk):
                if j < len(dm_list):
                    draft = dm_list[j]
                    if draft.channel == DraftChannel.DM:
                        body = (draft.body or "").strip()
                        if len(body) > 350:
                            logger.warning(
                                "Draft body over 350 chars, truncating",
                                extra={"opportunity_id": opp.id, "len": len(body)},
                            )
                            draft = DraftOutput(
                                channel=draft.channel,
                                message_type=draft.message_type,
                                subject=draft.subject,
                                body=body[:347] + "...",
                                personalization_notes=draft.personalization_notes,
                                cta=draft.cta,
                                recommended_angle=draft.recommended_angle,
                            )
                        drafts_repo.create_from_output(session, opp.id, draft)
                        drafts_created += 1
            session.commit()

        logger.info("Drafting completed", extra={"drafts_created": drafts_created})
    return drafts_created


def draft_for_run(session, run_id: int, limit: int = 20) -> int:
    """Draft DMs only for this run's scored, outreach-qualified opportunities. Returns number of drafts created."""
    anthropic_client = AnthropicClient()
    dm_system = _load_dm_prompt()
    debug_dir = get_debug_dir()
    drafts_created = 0

    def complete_fn(system: str, user_content: str, max_tokens: int = 512) -> str:
        return anthropic_client.performance_complete(system=system, user_content=user_content, max_tokens=max_tokens)

    def repair_batch_fn(raw: str) -> str:
        return repair_json_with_llm(raw, DRAFT_BATCH_HINT, lambda s, u: complete_fn(s, u, max_tokens=2048))

    prospect_ids = run_states_repo.list_prospect_ids_for_run(
        session, run_id, only_discovered=True, only_scored=True
    )
    from ..models import Prospect

    top_opps: List[Opportunity] = []
    for prospect_id in prospect_ids:
        opp = opp_repo.get_or_create_for_prospect(session, prospect_id)
        top_opps.append(opp)

    eligible: List[Tuple[Opportunity, object, List, str]] = []
    for opp in top_opps:
        if not is_outreach_qualified(opp):
            continue
        prospect = session.get(Prospect, opp.prospect_id)
        if not prospect:
            continue
        if contact_history_repo.recently_contacted(session, prospect.id, within_days=30):
            continue
        signals = list(signals_repo.list_for_prospect(session, prospect.id))
        context = _build_context(prospect, opp, signals)
        eligible.append((opp, prospect, signals, context))

    for i in range(0, len(eligible), DM_BATCH_SIZE):
        chunk = eligible[i : i + DM_BATCH_SIZE]
        batch_context = _build_batch_context(chunk)
        dm_raw = complete_fn(dm_system, batch_context, max_tokens=512 * len(chunk))
        dm_list, _ = get_structured(
            dm_raw,
            schema_class=DraftOutput,
            expect_list=True,
            step_name="draft_dm_batch",
            debug_dir=debug_dir,
            repair_fn=repair_batch_fn,
        )
        if not dm_list:
            for opp, _, _, _ in chunk:
                logger.error("DM drafting failed", extra={"opportunity_id": opp.id})
            continue
        for j, (opp, _, _, _) in enumerate(chunk):
            if j < len(dm_list):
                draft = dm_list[j]
                if draft.channel == DraftChannel.DM:
                    body = (draft.body or "").strip()
                    if len(body) > 350:
                        logger.warning(
                            "Draft body over 350 chars, truncating",
                            extra={"opportunity_id": opp.id, "len": len(body)},
                        )
                        draft = DraftOutput(
                            channel=draft.channel,
                            message_type=draft.message_type,
                            subject=draft.subject,
                            body=body[:347] + "...",
                            personalization_notes=draft.personalization_notes,
                            cta=draft.cta,
                            recommended_angle=draft.recommended_angle,
                        )
                    drafts_repo.create_from_output(session, opp.id, draft)
                    drafts_created += 1
        session.commit()

    logger.info("Drafting for run completed", extra={"run_id": run_id, "drafts_created": drafts_created})
    return drafts_created


