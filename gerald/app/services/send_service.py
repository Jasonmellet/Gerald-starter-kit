from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..clients.x_client import XClient, XClientError
from ..config import get_settings
from ..logging import get_logger
from ..models import Opportunity, Prospect, ProspectRunState
from ..repositories import contact_history as contact_history_repo
from ..repositories import drafts as drafts_repo
from ..repositories import prospect_run_states as run_states_repo
from ..repositories import opportunities as opp_repo
from ..repositories import prospects as prospects_repo
from ..services import drafting_service


logger = get_logger(__name__)

DM_V2_ENDPOINT = "POST /2/dm_conversations/with/{participant_id}/messages"


def _build_message_hash(prospect_id: int, opportunity_id: int, body: str) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(str(prospect_id).encode("utf-8"))
    h.update(str(opportunity_id).encode("utf-8"))
    h.update(body.encode("utf-8"))
    return h.hexdigest()


def send_dms_for_run(
    session: Session,
    run_id: int,
    opportunities: Optional[List[Opportunity]] = None,
    x_client: Optional[XClient] = None,
) -> Dict[str, object]:
    """
    Send or dry-run DMs for selected prospects in a run.

    Behavior is controlled by OUTREACH_SEND_MODE and ALLOW_LIVE_SEND:
    - dry_run or allow_live_send=False: log what would be sent, do not call X DM API.
    - live and allow_live_send=True: call X DM API and persist real send results.
    """
    settings = get_settings()
    is_live = settings.outreach_send_mode == "live" and settings.allow_live_send
    mode = "live" if is_live else "dry_run"

    # Load selected, not-yet-sent states for this run
    states: List[ProspectRunState] = run_states_repo.list_states_for_run(session, run_id, only_scored=False)
    candidates = [s for s in states if s.selected_for_outreach and not s.sent]

    details: List[Dict[str, object]] = []
    selected_count = len(candidates)
    attempted = 0
    live_sent = 0
    dry_run_count = 0
    skipped = 0
    failed = 0

    # Lazily create X client only if we actually need live sending
    dm_client: Optional[XClient] = None
    dm_client_error: Optional[str] = None

    for state in candidates:
        # ProspectRunState.prospect relationship should usually be populated; fall back to direct get
        prospect = state.prospect or session.get(Prospect, state.prospect_id)
        if not prospect:
            skipped += 1
            details.append(
                {
                    "prospect_id": state.prospect_id,
                    "status": "skipped",
                    "reason": "missing_prospect",
                }
            )
            continue

        opp = opp_repo.get_or_create_for_prospect(session, prospect.id)
        drafts = list(drafts_repo.list_for_opportunity(session, opp.id))
        dm_draft = next((d for d in drafts if d.channel == "dm"), None)

        # Validate draft
        if not dm_draft or not (dm_draft.body or "").strip():
            skipped += 1
            details.append(
                {
                    "prospect_id": prospect.id,
                    "opportunity_id": opp.id,
                    "status": "skipped",
                    "reason": "no_dm_draft",
                }
            )
            continue

        body = (dm_draft.body or "").strip()
        if len(body) > 320:
            shortened = drafting_service.shorten_draft_body(session, dm_draft, max_chars=320)
            if shortened:
                body = shortened
            else:
                skipped += 1
                details.append(
                    {
                        "prospect_id": prospect.id,
                        "opportunity_id": opp.id,
                        "status": "skipped",
                        "reason": "draft_too_long",
                    }
                )
                continue

        # Validate x_user_id (non-empty)
        x_user_id_val = (getattr(prospect, "x_user_id", None) or "").strip()
        if not x_user_id_val:
            skipped += 1
            details.append(
                {
                    "prospect_id": prospect.id,
                    "opportunity_id": opp.id,
                    "status": "skipped",
                    "reason": "no_x_user_id",
                }
            )
            continue

        # Recent contact suppression
        if contact_history_repo.recently_contacted(
            session, prospect.id, within_days=settings.recent_contact_suppression_days
        ):
            skipped += 1
            details.append(
                {
                    "prospect_id": prospect.id,
                    "opportunity_id": opp.id,
                    "status": "skipped",
                    "reason": "recently_contacted",
                }
            )
            continue

        # Opportunity status check
        if getattr(opp, "status", "").lower() == "contacted":
            skipped += 1
            details.append(
                {
                    "prospect_id": prospect.id,
                    "opportunity_id": opp.id,
                    "status": "skipped",
                    "reason": "opportunity_already_contacted",
                }
            )
            continue

        # Skip prospects we know cannot receive DMs (e.g. X 403 from a previous run)
        if getattr(prospect, "cannot_receive_dm", False):
            skipped += 1
            details.append(
                {
                    "prospect_id": prospect.id,
                    "opportunity_id": opp.id,
                    "status": "skipped",
                    "reason": "dm_not_allowed",
                }
            )
            continue

        attempted += 1
        message_hash = _build_message_hash(prospect.id, opp.id, body)

        if not is_live:
            # Dry-run: record what would be sent, but do not mark as sent/ contacted
            contact_history_repo.record_contact(
                session,
                prospect_id=prospect.id,
                opportunity_id=opp.id,
                channel="x_dm",
                message_hash=message_hash,
                run_id=run_id,
                model_used=settings.anthropic_strong_model,
                send_status="dry_run",
            )
            dry_run_count += 1
            details.append(
                {
                    "prospect_id": prospect.id,
                    "handle": prospect.handle,
                    "x_user_id": prospect.x_user_id,
                    "opportunity_id": opp.id,
                    "status": "dry_run",
                    "endpoint": DM_V2_ENDPOINT,
                    "participant_id": prospect.x_user_id,
                    "send_result": "dry_run",
                    "body": body,
                }
            )
            continue

        # Live sending
        if dm_client is None and dm_client_error is None:
            try:
                dm_client = x_client or XClient()
            except XClientError as exc:
                dm_client_error = str(exc)
                logger.error(
                    "X DM client initialization failed; marking sends as failed",
                    extra={"error": dm_client_error},
                )

        if dm_client is None:
            # Cannot send; record failure but do not mark sent
            failed += 1
            contact_history_repo.record_contact(
                session,
                prospect_id=prospect.id,
                opportunity_id=opp.id,
                channel="x_dm",
                message_hash=message_hash,
                run_id=run_id,
                model_used=settings.anthropic_strong_model,
                send_status="failed",
                error_message=dm_client_error or "DM client unavailable",
            )
            details.append(
                {
                    "prospect_id": prospect.id,
                    "opportunity_id": opp.id,
                    "status": "failed",
                    "error": dm_client_error or "DM client unavailable",
                    "endpoint": DM_V2_ENDPOINT,
                    "participant_id": prospect.x_user_id,
                    "send_result": dm_client_error or "DM client unavailable",
                }
            )
            continue

        try:
            resp = dm_client.send_direct_message(recipient_user_id=x_user_id_val, text=body)
            external_id = resp.get("external_message_id")
            contact_history_repo.record_contact(
                session,
                prospect_id=prospect.id,
                opportunity_id=opp.id,
                channel="x_dm",
                message_hash=message_hash,
                run_id=run_id,
                model_used=settings.anthropic_strong_model,
                send_status="sent",
                external_message_id=external_id,
            )
            run_states_repo.mark_sent(session, run_id, prospect.id)
            # Update opportunity status to contacted if attribute exists
            if hasattr(opp, "status"):
                from ..constants import OpportunityStatus  # type: ignore[import]

                try:
                    opp.status = OpportunityStatus.CONTACTED.value  # type: ignore[assignment]
                except Exception:
                    opp.status = "contacted"  # fallback
            live_sent += 1
            details.append(
                {
                    "prospect_id": prospect.id,
                    "handle": prospect.handle,
                    "x_user_id": prospect.x_user_id,
                    "opportunity_id": opp.id,
                    "status": "sent",
                    "endpoint": DM_V2_ENDPOINT,
                    "participant_id": prospect.x_user_id,
                    "send_result": "sent",
                    "external_message_id": external_id,
                }
            )
            # In live mode, stop once we've sent enough (go down list only until target reached)
            if is_live and live_sent >= settings.daily_outreach_limit:
                break
        except XClientError as exc:
            failed += 1
            # Tag prospect so we don't try to DM them again (X 403 = recipient doesn't allow DMs from us)
            if "do not have permission to DM" in str(exc).lower() or "one or more participants" in str(exc).lower():
                try:
                    prospect.cannot_receive_dm = True
                    session.flush()
                except Exception:
                    pass
            contact_history_repo.record_contact(
                session,
                prospect_id=prospect.id,
                opportunity_id=opp.id,
                channel="x_dm",
                message_hash=message_hash,
                run_id=run_id,
                model_used=settings.anthropic_strong_model,
                send_status="failed",
                error_message=str(exc),
            )
            details.append(
                {
                    "prospect_id": prospect.id,
                    "opportunity_id": opp.id,
                    "status": "failed",
                    "error": str(exc),
                    "endpoint": DM_V2_ENDPOINT,
                    "participant_id": prospect.x_user_id,
                    "send_result": str(exc),
                }
            )

    session.commit()

    summary: Dict[str, object] = {
        "run_id": run_id,
        "mode": mode,
        "selected_candidates": selected_count,
        "attempted": attempted,
        "live_sent": live_sent,
        "dry_run": dry_run_count,
        "skipped": skipped,
        "failed": failed,
        "details": details,
    }
    return summary
