from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.constants import DraftChannel
from app.models import Base, ContactHistory, Draft, Opportunity, PipelineRun, Prospect, ProspectRunState
from app.repositories import contact_history as contact_history_repo
from app.repositories import drafts as drafts_repo
from app.schemas import DraftOutput
from app.services import send_service


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_prospect(handle: str, x_user_id: str, display_name: Optional[str] = None) -> Prospect:
    """Minimal valid Prospect for send_service tests (all non-nullable fields set)."""
    return Prospect(
        handle=handle,
        x_user_id=x_user_id,
        display_name=display_name or handle,
        bio="",
        location="",
        website="",
        follower_count=0,
        following_count=0,
        tweet_count=0,
        account_created_at=datetime.now(timezone.utc),
        role_guess="",
        company_guess="",
        fit_notes="",
    )


def _make_opportunity(prospect_id: int) -> Opportunity:
    """Minimal valid Opportunity for send_service tests (all non-nullable fields set)."""
    return Opportunity(
        prospect_id=prospect_id,
        overall_score=0.0,
        urgency_score=0.0,
        fit_score=0.0,
        buyer_score=0.0,
        outreach_score=0.0,
        confidence_score=0.0,
        why_now="",
        recommended_angle="",
        summary="",
    )


def test_send_dms_for_run_dry_run_path():
    # Configure settings for dry_run
    settings = get_settings()
    settings.outreach_send_mode = "dry_run"
    settings.allow_live_send = False

    session: Session = _make_session()
    run = PipelineRun(
        started_at=datetime.now(timezone.utc),
        discovery_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        discovery_window_end=datetime.now(timezone.utc),
        discovery_limit=10,
    )
    session.add(run)
    session.flush()

    prospect = _make_prospect("test", "123")
    session.add(prospect)
    session.flush()

    opp = _make_opportunity(prospect.id)
    session.add(opp)
    session.flush()

    _add_dm_draft(session, opp.id)
    state = ProspectRunState(run_id=run.id, prospect_id=prospect.id, included_in_discovery=True, scored=True, selected_for_outreach=True)
    session.add(state)
    session.commit()

    summary = send_service.send_dms_for_run(session, run.id)

    assert summary["mode"] == "dry_run"
    count = session.query(ContactHistory).count()
    assert count >= 1


def test_send_dms_for_run_skips_recently_contacted():
    settings = get_settings()
    settings.outreach_send_mode = "dry_run"
    settings.allow_live_send = False

    session: Session = _make_session()
    run = PipelineRun(
        started_at=datetime.now(timezone.utc),
        discovery_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        discovery_window_end=datetime.now(timezone.utc),
        discovery_limit=10,
    )
    session.add(run)
    session.flush()

    prospect = _make_prospect("test2", "456")
    session.add(prospect)
    session.flush()

    opp = _make_opportunity(prospect.id)
    session.add(opp)
    session.flush()

    _add_dm_draft(session, opp.id)
    state = ProspectRunState(run_id=run.id, prospect_id=prospect.id, included_in_discovery=True, scored=True, selected_for_outreach=True)
    session.add(state)
    session.flush()

    # Seed recent contact
    contact_history_repo.record_contact(
        session,
        prospect_id=prospect.id,
        opportunity_id=opp.id,
        channel="x_dm",
    )
    session.commit()

    summary = send_service.send_dms_for_run(session, run.id)
    # Should be counted as skipped
    assert summary["skipped"] >= 1


def _add_dm_draft(session: Session, opportunity_id: int, body: str = "Test DM body") -> None:
    drafts_repo.create_from_output(
        session,
        opportunity_id,
        DraftOutput(channel=DraftChannel.DM, message_type="dm_intro", body=body),
    )
    session.flush()


class SuccessV2Client:
    """Mock client that simulates successful v2 DM send."""

    def send_direct_message(self, recipient_user_id: str, text: str):
        return {"ok": True, "status_code": 200, "external_message_id": "e123", "raw": {}}


def test_send_dms_for_run_v2_success_path():
    settings = get_settings()
    settings.outreach_send_mode = "live"
    settings.allow_live_send = True

    session: Session = _make_session()
    run = PipelineRun(
        started_at=datetime.now(timezone.utc),
        discovery_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        discovery_window_end=datetime.now(timezone.utc),
        discovery_limit=10,
    )
    session.add(run)
    session.flush()

    prospect = _make_prospect("v2test", "999888")
    session.add(prospect)
    session.flush()

    opp = _make_opportunity(prospect.id)
    session.add(opp)
    session.flush()

    _add_dm_draft(session, opp.id)
    state = ProspectRunState(
        run_id=run.id,
        prospect_id=prospect.id,
        included_in_discovery=True,
        scored=True,
        selected_for_outreach=True,
    )
    session.add(state)
    session.commit()

    summary = send_service.send_dms_for_run(session, run.id, x_client=SuccessV2Client())
    assert summary["live_sent"] == 1
    assert summary["failed"] == 0
    sent_details = [d for d in summary["details"] if d.get("status") == "sent"]
    assert len(sent_details) == 1
    assert sent_details[0].get("endpoint") == "POST /2/dm_conversations/with/{participant_id}/messages"
    assert sent_details[0].get("participant_id") == "999888"
    assert sent_details[0].get("send_result") == "sent"


def test_send_dms_for_run_skips_when_x_user_id_missing():
    settings = get_settings()
    settings.outreach_send_mode = "live"
    settings.allow_live_send = True

    session: Session = _make_session()
    run = PipelineRun(
        started_at=datetime.now(timezone.utc),
        discovery_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        discovery_window_end=datetime.now(timezone.utc),
        discovery_limit=10,
    )
    session.add(run)
    session.flush()

    prospect = _make_prospect("noxid", "")  # empty x_user_id
    session.add(prospect)
    session.flush()

    opp = _make_opportunity(prospect.id)
    session.add(opp)
    session.flush()

    _add_dm_draft(session, opp.id)
    state = ProspectRunState(
        run_id=run.id,
        prospect_id=prospect.id,
        included_in_discovery=True,
        scored=True,
        selected_for_outreach=True,
    )
    session.add(state)
    session.commit()

    summary = send_service.send_dms_for_run(session, run.id, x_client=SuccessV2Client())
    assert summary["skipped"] >= 1
    skip_details = [d for d in summary["details"] if d.get("reason") == "no_x_user_id"]
    assert len(skip_details) >= 1
    assert summary["live_sent"] == 0


class FailingClient:
    def send_direct_message(self, recipient_user_id: str, text: str):
        from app.clients.x_client import XClientError

        raise XClientError("boom")


class FailingClientWithResponseBody:
    """Raises XClientError with response_body so we can assert it is stored."""

    def send_direct_message(self, recipient_user_id: str, text: str):
        from app.clients.x_client import XClientError

        raise XClientError(
            "DM API returned 403",
            status_code=403,
            response_body='{"errors":[{"code":453}]}',
        )


def test_send_dms_for_run_handles_api_error():
    settings = get_settings()
    settings.outreach_send_mode = "live"
    settings.allow_live_send = True

    session: Session = _make_session()
    run = PipelineRun(
        started_at=datetime.now(timezone.utc),
        discovery_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        discovery_window_end=datetime.now(timezone.utc),
        discovery_limit=10,
    )
    session.add(run)
    session.flush()

    prospect = _make_prospect("test3", "789")
    session.add(prospect)
    session.flush()

    opp = _make_opportunity(prospect.id)
    session.add(opp)
    session.flush()

    _add_dm_draft(session, opp.id)
    state = ProspectRunState(
        run_id=run.id,
        prospect_id=prospect.id,
        included_in_discovery=True,
        scored=True,
        selected_for_outreach=True,
    )
    session.add(state)
    session.commit()

    summary = send_service.send_dms_for_run(session, run.id, x_client=FailingClient())
    assert summary["failed"] >= 1


def test_send_dms_for_run_failed_api_stores_full_response_body():
    settings = get_settings()
    settings.outreach_send_mode = "live"
    settings.allow_live_send = True

    session: Session = _make_session()
    run = PipelineRun(
        started_at=datetime.now(timezone.utc),
        discovery_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
        discovery_window_end=datetime.now(timezone.utc),
        discovery_limit=10,
    )
    session.add(run)
    session.flush()

    prospect = _make_prospect("test4", "111")
    session.add(prospect)
    session.flush()

    opp = _make_opportunity(prospect.id)
    session.add(opp)
    session.flush()

    _add_dm_draft(session, opp.id)
    state = ProspectRunState(
        run_id=run.id,
        prospect_id=prospect.id,
        included_in_discovery=True,
        scored=True,
        selected_for_outreach=True,
    )
    session.add(state)
    session.commit()

    summary = send_service.send_dms_for_run(session, run.id, x_client=FailingClientWithResponseBody())
    assert summary["failed"] >= 1
    failed_details = [d for d in summary["details"] if d.get("status") == "failed"]
    assert len(failed_details) >= 1
    assert '{"errors":[{"code":453}]}' in str(failed_details[0].get("error", ""))
    # Stored in contact_history as error_message
    recs = session.query(ContactHistory).filter(ContactHistory.send_status == "failed").all()
    assert any('{"errors":[{"code":453}]}' in (r.error_message or "") for r in recs)

