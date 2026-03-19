#!/usr/bin/env python3
"""
Meeting bot: Gmail invites -> Recall.ai bot -> transcript -> summary + email.
Run from repo root or meeting_bot dir. Loads .env from meeting_bot/.

  python -m meeting_bot.run --once       # one poll then exit (for cron/LaunchAgent)
  python -m meeting_bot.run --loop       # poll every 5 min
  python -m meeting_bot.run --auth-only  # Gmail OAuth only
"""
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Run from meeting_bot so .env and relative paths resolve
BASE = Path(__file__).resolve().parent
if os.getcwd() != str(BASE):
    os.chdir(BASE)
sys.path.insert(0, str(BASE))

import config
config.load_env()

from recall_client import RecallAIClient
from gmail_client import GmailClient
from processor import MeetingProcessor


def _meeting_info_for_processor(invite: dict) -> dict:
    """Build meeting_info with date for processor/save."""
    out = {
        "subject": invite.get("subject", "Meeting"),
        "start_time": invite.get("start_time"),
        "end_time": invite.get("end_time"),
        "meeting_url": invite.get("meeting_url"),
    }
    st = invite.get("start_time")
    if st:
        try:
            # ISO -> YYYY-MM-DD
            out["date"] = st[:10] if len(st) >= 10 else datetime.now().strftime("%Y-%m-%d")
        except Exception:
            out["date"] = datetime.now().strftime("%Y-%m-%d")
    else:
        out["date"] = datetime.now().strftime("%Y-%m-%d")
    return out


def _invite_ended(invite: dict) -> bool:
    et = invite.get("end_time") or invite.get("start_time")
    if not et:
        return False
    try:
        end_dt = datetime.fromisoformat(et.replace("Z", "+00:00"))
        return datetime.now(end_dt.tzinfo) > end_dt
    except Exception:
        return False


def _should_join(invite: dict, active_bots: dict, join_enabled: bool) -> bool:
    if not join_enabled:
        return False
    meeting_url = invite.get("meeting_url")
    msg_id = invite.get("message_id")
    for bot_id, info in list(active_bots.items()):
        existing = info.get("invite", {})
        if existing.get("meeting_url") != meeting_url:
            continue
        if existing.get("message_id") == msg_id:
            return False
        # Reschedule: same URL, different msg_id
        try:
            RecallAIClient().delete_bot(bot_id)
        except Exception:
            pass
        del active_bots[bot_id]
        break
    start_time = invite.get("start_time")
    if not start_time:
        return False
    try:
        meeting_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        now = datetime.now(meeting_dt.tzinfo)
        end_time = invite.get("end_time")
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            if now > end_dt:
                return False
        window_min = int(os.environ.get("JOIN_WINDOW_MINUTES", "15"))
        grace_min = int(os.environ.get("JOIN_GRACE_MINUTES", "5"))
        window_sec = window_min * 60
        grace_sec = -grace_min * 60
        time_diff = (meeting_dt - now).total_seconds()
        if time_diff > window_sec or time_diff < grace_sec:
            return False
        return True
    except Exception:
        return False


def run_once(recheck_all: bool = False) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state_file = config.STATE_FILE
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            pass
    processed = set(state.get("processed_invites", []))
    active_bots = state.get("active_bots", {})  # bot_id -> { invite, status }

    recall = RecallAIClient()
    creds_path = config.get("GMAIL_CREDENTIALS_PATH") or str(config.GMAIL_CREDENTIALS)
    token_path = config.get("GMAIL_TOKEN_PATH") or str(config.GMAIL_TOKEN)
    if not Path(creds_path).is_absolute():
        creds_path = str(config.BASE_DIR / creds_path)
    if not Path(token_path).is_absolute():
        token_path = str(config.BASE_DIR / token_path)
    gmail = GmailClient(
        credentials_path=creds_path,
        token_path=token_path,
        use_send_scope=True,
    )
    if not gmail.authenticate():
        print("Gmail auth failed")
        return
    processor = MeetingProcessor()
    join_enabled = os.environ.get("JOIN_ENABLED", "true").lower() not in ("0", "false", "no", "off")
    summary_to = config.get("SUMMARY_EMAIL_TO", "").strip() or gmail.email_address

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling...")
    # 1) Check completed bots -> transcript -> process -> save -> email
    for bot_id, info in list(active_bots.items()):
        try:
            bot = recall.get_bot(bot_id)
            status = bot.get("status")
            info["status"] = status
            if status not in ("done", "failed", "kicked", "left"):
                continue
            invite = info.get("invite", {})
            transcript = recall.get_transcript(bot_id) if status == "done" else None
            if transcript:
                meeting_info = _meeting_info_for_processor(invite)
                analysis = processor.process_transcript(transcript, meeting_info)
                filepath = processor.save_analysis(analysis, str(config.OUTPUT_DIR))
                print(f"  Saved: {filepath}")
                # Email
                if summary_to:
                    body = _build_email_body(analysis, filepath)
                    subject = f"Meeting Summary: {meeting_info.get('subject', 'Meeting')} - {meeting_info.get('date', '')}"
                    gmail.send_email(to=summary_to, subject=subject, body=body)
                    print(f"  Email sent to {summary_to}")
            try:
                recall.delete_bot(bot_id)
            except Exception:
                pass
            del active_bots[bot_id]
            processed.add(invite.get("message_id"))
        except Exception as e:
            print(f"  Error processing bot {bot_id}: {e}")
    # 2) New invites
    invites = gmail.get_calendar_invites(max_results=50)
    for invite in invites:
        msg_id = invite.get("message_id")
        if not recheck_all and msg_id in processed:
            continue
        meeting_url = invite.get("meeting_url")
        if not meeting_url:
            continue
        already_has_bot = any(
            info.get("invite", {}).get("message_id") == msg_id
            for info in active_bots.values()
        )
        if already_has_bot:
            processed.add(msg_id)
            continue
        if _invite_ended(invite):
            processed.add(msg_id)
            continue
        should = _should_join(invite, active_bots, join_enabled)
        if should:
            try:
                bot = recall.create_bot(
                    meeting_url=meeting_url,
                    name=os.environ.get("BOT_NAME", "Notetaker"),
                    transcription=True,
                )
                bid = bot.get("id")
                active_bots[bid] = {"invite": invite, "status": "created"}
                print(f"  Bot created: {bid[:8]}... for {invite.get('subject', '?')}")
            except Exception as e:
                print(f"  Error creating bot: {e}")
        processed.add(msg_id)

    state["processed_invites"] = list(processed)
    state["active_bots"] = {
        k: {"invite": v.get("invite"), "status": v.get("status")}
        for k, v in active_bots.items()
    }
    state["last_saved"] = datetime.now().isoformat()
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))


def _build_email_body(analysis: dict, filepath: str) -> str:
    meeting_info = analysis.get("meeting_info", {})
    summary = analysis.get("summary", {})
    raw = (analysis.get("raw_text") or "")[:3000]
    if len(analysis.get("raw_text") or "") > 3000:
        raw += "\n\n... (truncated)"
    lines = [
        f"# Meeting Summary: {meeting_info.get('subject', 'Meeting')}",
        "",
        f"**Date:** {meeting_info.get('date', '')}",
        f"**Topics:** {', '.join(summary.get('key_topics', []))}",
        "",
        "## Transcript excerpt",
        "",
        raw or "No transcript.",
        "",
        "## Action Items",
        "",
    ]
    for item in analysis.get("action_items", []):
        lines.append(f"- [{item.get('speaker', '?')}] {item.get('text', '')}")
    lines.append("")
    lines.append("## Customers mentioned")
    for name, data in (analysis.get("customers") or {}).items():
        lines.append(f"- **{name}**: {data.get('mention_count', 0)} mention(s)")
    lines.extend(["", "---", f"Full analysis: {filepath}"])
    return "\n".join(lines)


def main():
    import argparse
    p = argparse.ArgumentParser(description="Meeting bot: Gmail + Recall.ai -> transcript + email")
    p.add_argument("--once", action="store_true", help="Run one poll and exit")
    p.add_argument("--loop", action="store_true", help="Poll every 5 min")
    p.add_argument("--recheck", action="store_true", help="Re-evaluate all invites (with --once)")
    p.add_argument("--auth-only", action="store_true", help="Gmail OAuth only, then exit")
    args = p.parse_args()

    if args.auth_only:
        config.load_env()
        config.CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        creds_path = config.get("GMAIL_CREDENTIALS_PATH") or str(config.GMAIL_CREDENTIALS)
        token_path = config.get("GMAIL_TOKEN_PATH") or str(config.GMAIL_TOKEN)
        if not Path(creds_path).is_absolute():
            creds_path = str(config.BASE_DIR / creds_path)
        if not Path(token_path).is_absolute():
            token_path = str(config.BASE_DIR / token_path)
        gmail = GmailClient(
            credentials_path=creds_path,
            token_path=token_path,
            use_send_scope=True,
        )
        if gmail.authenticate():
            print(f"OK: {gmail.email_address}")
        else:
            print("Auth failed")
            sys.exit(1)
        return

    if args.loop:
        while True:
            run_once(recheck_all=False)
            print("  Next poll in 300s")
            time.sleep(300)
    else:
        run_once(recheck_all=args.recheck)


if __name__ == "__main__":
    main()
