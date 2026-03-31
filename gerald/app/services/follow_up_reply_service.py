from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..clients.anthropic_client import AnthropicClient
from ..clients.x_client import XClient, XClientError
from ..logging import get_logger
from ..models import ContactHistory, Prospect
from ..repositories import contact_history as contact_history_repo


logger = get_logger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "follow_up_reply_question.txt"
MAX_REPLY_LEN = 280


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _generate_question(tweet_text: str) -> Optional[str]:
    """Generate one short question about the tweet (max 280 chars). Returns None on failure."""
    if not (tweet_text or "").strip():
        return None
    try:
        client = AnthropicClient()
        prompt_template = _load_prompt()
        user_content = prompt_template.replace("{{tweet_text}}", (tweet_text or "").strip())
        system = "You output a single conversational question. No quotes or preamble."
        out = client.performance_complete(system=system, user_content=user_content, max_tokens=150)
        question = (out or "").strip().strip('"').strip("'")
        if not question:
            return None
        if len(question) > MAX_REPLY_LEN:
            question = question[: MAX_REPLY_LEN - 3] + "..."
        return question
    except Exception as e:
        logger.warning("Follow-up question generation failed", extra={"error": str(e)})
        return None


def _is_reply_policy_403(error: XClientError) -> bool:
    """True if this is X's 403 'reply not allowed' policy (mention/engage required)."""
    msg = (getattr(error, "response_body", None) or str(error)) or ""
    return "403" in str(getattr(error, "status_code", "")) and (
        "not allowed" in msg and "mentioned or otherwise engaged" in msg
    )


def send_replies_for_run(
    session: Session,
    run_id: int,
    x_client: Optional[XClient] = None,
) -> Dict[str, object]:
    """
    For each contact in this run that was sent a DM and has no reply yet:
    fetch their latest tweet, generate a question, post a public reply, record reply_tweet_id.
    Waterfall: if X returns 403 (reply policy), mark contact as skipped and continue to next.
    """
    contacts: List[ContactHistory] = contact_history_repo.list_sent_without_reply_for_run(session, run_id)
    eligible = len(contacts)
    replies_sent = 0
    skipped_no_tweet = 0
    skipped_no_question = 0
    skipped_reply_policy = 0
    failed = 0

    if eligible == 0:
        return {
            "contacts_eligible": 0,
            "replies_sent": 0,
            "skipped_no_tweet": 0,
            "skipped_no_question": 0,
            "skipped_reply_policy": 0,
            "failed": 0,
        }

    client = x_client
    if client is None:
        try:
            client = XClient()
        except XClientError as e:
            logger.error("X client unavailable for follow-up replies", extra={"error": str(e)})
            return {
                "contacts_eligible": eligible,
                "replies_sent": 0,
                "skipped_no_tweet": 0,
                "skipped_no_question": 0,
                "skipped_reply_policy": 0,
                "failed": eligible,
            }

    for contact in contacts:
        prospect: Optional[Prospect] = session.get(Prospect, contact.prospect_id)
        if not prospect or not (getattr(prospect, "x_user_id", None) or "").strip():
            failed += 1
            continue

        x_user_id = (prospect.x_user_id or "").strip()

        # Fetch latest tweet (bearer-token read)
        try:
            tweets = client.get_user_posts(x_user_id, limit=1)
        except Exception as e:
            logger.warning("get_user_posts failed for follow-up", extra={"prospect_id": prospect.id, "error": str(e)})
            failed += 1
            continue

        if not tweets or not isinstance(tweets, list):
            skipped_no_tweet += 1
            continue

        tweet = tweets[0] if tweets else None
        if not tweet or not isinstance(tweet, dict):
            skipped_no_tweet += 1
            continue

        tweet_id = tweet.get("id")
        tweet_text = tweet.get("text") or ""

        if not tweet_id:
            skipped_no_tweet += 1
            continue

        question = _generate_question(tweet_text)
        if not question:
            skipped_no_question += 1
            continue

        try:
            result = client.create_reply(in_reply_to_tweet_id=str(tweet_id), text=question)
            new_tweet_id = result.get("tweet_id")
            if new_tweet_id:
                contact_history_repo.set_reply_tweet_id(session, contact.id, str(new_tweet_id))
                replies_sent += 1
                logger.info(
                    "Follow-up reply posted",
                    extra={"contact_id": contact.id, "reply_tweet_id": new_tweet_id, "prospect_id": prospect.id},
                )
            else:
                failed += 1
        except XClientError as e:
            if _is_reply_policy_403(e):
                contact_history_repo.set_reply_skipped_reason(session, contact.id, "x_policy")
                skipped_reply_policy += 1
                logger.info(
                    "Follow-up reply skipped (X policy: reply only when author mentioned/quoted you)",
                    extra={"contact_id": contact.id, "prospect_id": prospect.id, "handle": prospect.handle},
                )
            else:
                logger.warning(
                    "create_reply failed for follow-up",
                    extra={"contact_id": contact.id, "prospect_id": prospect.id, "error": str(e)},
                )
                failed += 1

    session.commit()

    return {
        "contacts_eligible": eligible,
        "replies_sent": replies_sent,
        "skipped_no_tweet": skipped_no_tweet,
        "skipped_no_question": skipped_no_question,
        "skipped_reply_policy": skipped_reply_policy,
        "failed": failed,
    }
