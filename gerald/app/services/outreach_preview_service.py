from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from ..models import Prospect, Opportunity, ProspectRunState
from ..repositories import drafts as drafts_repo
from ..repositories import opportunities as opp_repo
from ..repositories import prospect_run_states as run_states_repo
from ..repositories import prospects as prospects_repo


def get_run_outreach_preview(session: Session, run_id: int, include_sent: bool = True) -> List[Dict[str, object]]:
    """
    Return preview rows for a run's selected prospects, ordered by priority_score desc.
    Each row contains handle, x_user_id, priority_score, freshness_hours, opportunity_id, draft_body.
    """
    states: List[ProspectRunState] = run_states_repo.list_states_for_run(session, run_id, only_scored=False)
    rows: List[Dict[str, object]] = []
    for state in states:
        if not state.selected_for_outreach:
            continue
        if not include_sent and state.sent:
            continue
        prospect = state.prospect or prospects_repo.get_by_id(session, state.prospect_id) if hasattr(
            prospects_repo, "get_by_id"
        ) else session.get(Prospect, state.prospect_id)
        if not prospect:
            continue
        opp: Opportunity = opp_repo.get_or_create_for_prospect(session, prospect.id)
        drafts = list(drafts_repo.list_for_opportunity(session, opp.id))
        dm_draft = next((d for d in drafts if d.channel == "dm"), None)
        draft_body = (dm_draft.body or "").strip() if dm_draft and dm_draft.body else ""
        rows.append(
            {
                "prospect_id": prospect.id,
                "handle": prospect.handle,
                "x_user_id": getattr(prospect, "x_user_id", None),
                "priority_score": state.priority_score,
                "freshness_hours": state.freshness_hours,
                "opportunity_id": opp.id,
                "draft_body": draft_body,
            }
        )
    rows.sort(key=lambda r: (-(r.get("priority_score") or 0.0)))
    return rows

