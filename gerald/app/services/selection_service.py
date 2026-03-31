from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..models import Opportunity, Prospect
from ..repositories import contact_history as contact_history_repo
from ..repositories import drafts as drafts_repo
from ..repositories import opportunities as opp_repo
from ..repositories import posts as posts_repo
from ..repositories import prospect_run_states as run_states_repo
from ..services.scoring_service import is_outreach_qualified

FRESHNESS_EXCLUDE_HOURS = 24 * 7  # 7 days


def compute_freshness_hours(session, prospect_id: int, reference: Optional[datetime] = None) -> float:
    """Hours since prospect's most recent post. If no posts, return large value (stale)."""
    posts = list(posts_repo.list_for_prospect(session, prospect_id))
    ref = reference or datetime.now(timezone.utc)
    if not posts:
        return 9999.0
    latest = max((p.posted_at for p in posts if p.posted_at), default=None)
    if not latest:
        return 9999.0
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    delta = ref - latest
    return max(0.0, delta.total_seconds() / 3600.0)


def compute_freshness_penalty(freshness_hours: float) -> float:
    """Penalty to subtract from composite score. <=24h: 0, 24-72h: small, 3-7d: medium, >7d: exclude (caller checks)."""
    if freshness_hours <= 24:
        return 0.0
    if freshness_hours <= 72:
        return 5.0
    if freshness_hours <= FRESHNESS_EXCLUDE_HOURS:
        return 15.0
    return 999.0


def select_top_for_run(session, run_id: int, limit: int = 5) -> List[Opportunity]:
    """
    Select top `limit` opportunities from this run. Exclude: contacted 30d, brand, no draft, below threshold, freshness > 7d.
    Rank by: urgency desc, buyer desc, fit desc, outreach desc, confidence desc, freshness asc.
    """
    from ..services.discovery_service import _is_likely_brand_account

    states = run_states_repo.list_states_for_run(session, run_id, only_scored=True)
    prospect_ids = [s.prospect_id for s in states]
    if not prospect_ids:
        return []

    # Load opportunities and prospects for this run
    opps = []
    for prospect_id in prospect_ids:
        opp = opp_repo.get_or_create_for_prospect(session, prospect_id)
        prospect = session.get(Prospect, prospect_id)
        if not prospect:
            continue
        opps.append((opp, prospect))

    # Filter and compute freshness
    candidates = []
    for opp, prospect in opps:
        if not prospect:
            continue
        if getattr(prospect, "cannot_receive_dm", False):
            run_states_repo.set_excluded(session, run_id, prospect.id, "dm_not_allowed")
            continue
        if not is_outreach_qualified(opp):
            run_states_repo.set_excluded(session, run_id, prospect.id, "below_outreach_threshold")
            continue
        if contact_history_repo.recently_contacted(session, prospect.id, within_days=30):
            run_states_repo.set_excluded(session, run_id, prospect.id, "contacted_recently")
            continue
        if _is_likely_brand_account(prospect.bio or "", prospect.handle or ""):
            run_states_repo.set_excluded(session, run_id, prospect.id, "brand_account")
            continue
        drafts = list(drafts_repo.list_for_opportunity(session, opp.id))
        dm_draft = next((d for d in drafts if d.channel == "dm"), None)
        if not dm_draft or not (dm_draft.body or "").strip():
            run_states_repo.set_excluded(session, run_id, prospect.id, "no_dm_draft")
            continue
        freshness = compute_freshness_hours(session, prospect.id)
        run_states_repo.set_freshness(session, run_id, prospect.id, freshness)
        if freshness > FRESHNESS_EXCLUDE_HOURS:
            run_states_repo.set_excluded(session, run_id, prospect.id, "freshness_over_7_days")
            continue
        penalty = compute_freshness_penalty(freshness)
        urgency = opp.urgency_score or 0
        buyer = opp.buyer_score or 0
        fit = opp.fit_score or 0
        outreach = opp.outreach_score or 0
        confidence = opp.confidence_score or 0
        priority = urgency + buyer + fit + outreach + confidence - penalty
        run_states_repo.set_priority_score(session, run_id, prospect.id, priority)
        candidates.append((priority, freshness, opp))

    # Sort: priority desc, then freshness asc (fresher first)
    candidates.sort(key=lambda x: (-x[0], x[1]))
    selected = [c[2] for c in candidates[:limit]]
    for opp in selected:
        run_states_repo.mark_selected(session, run_id, opp.prospect_id, priority_score=None)
    session.commit()
    return selected
