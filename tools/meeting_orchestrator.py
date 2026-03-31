"""
Meeting Orchestrator for OpenClaw
Coordinates Gmail monitoring, Recall.ai bot management, and transcript processing.
"""

import os

# Load .env from repo root: Openclaw/.env (one level up from tools/)
def _load_env():
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _env_file = os.path.join(_root, ".env")
    if not os.path.exists(_env_file):
        return
    with open(_env_file, "r") as f:
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if k.strip() and v:
                os.environ.setdefault(k.strip(), v)
_load_env()

import json
import time
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path

from recall_client import RecallAIClient
from gmail_client import GmailClient
from meeting_processor import MeetingProcessor
from sessions_send import sessions_send


class MeetingOrchestrator:
    """
    Main orchestrator for the meeting transcription workflow.
    
    Flow:
    1. Monitor Gmail for calendar invites
    2. Extract meeting URLs
    3. Schedule Recall.ai bots to join meetings
    4. Wait for completion
    5. Retrieve and process transcripts
    6. Save analysis to memory/meetings/
    """
    
    def __init__(
        self,
        poll_interval: int = 60,
        meetings_dir: str = "memory/meetings",
        state_file: str = "memory/meeting-state.json"
    ):
        """
        Initialize orchestrator.
        
        Args:
            poll_interval: Seconds between Gmail checks
            meetings_dir: Where to save meeting analyses
            state_file: Path to persistent state file
        """
        self.poll_interval = poll_interval
        self.meetings_dir = meetings_dir
        self.state_file = state_file
        self.invite_scan_limit = int(os.environ.get("MEETING_INVITE_SCAN_LIMIT", "200"))
        self.waiting_room_timeout_minutes = int(os.environ.get("RECALL_WAITING_ROOM_TIMEOUT_MINUTES", "20"))
        self.waiting_room_alert_minutes = int(os.environ.get("RECALL_WAITING_ROOM_ALERT_MINUTES", "2"))
        self.alert_telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "8130598479")
        
        # Clients
        self.recall = None
        self.gmail = None
        self.processor = MeetingProcessor()
        
        # State
        self.running = False
        self.processed_invites = set()
        self.active_bots = {}  # bot_id -> meeting_info
        self.scheduled_meetings = {}  # meeting_url -> scheduled_time
        self.waiting_room_alerted_bots = set()
        
        # Load state
        self._load_state()
    
    def initialize(self) -> bool:
        """Initialize all clients and authenticate."""
        try:
            # Initialize Recall.ai
            print("Initializing Recall.ai client...")
            self.recall = RecallAIClient()
            
            # Test connection
            bots = self.recall.list_bots()
            print(f"✓ Recall.ai connected ({len(bots)} existing bots)")
            
            # Initialize Gmail
            print("Initializing Gmail client...")
            self.gmail = GmailClient()
            
            # This will trigger OAuth flow if needed
            if not self.gmail.authenticate():
                print("✗ Gmail authentication failed")
                return False
            
            print(f"✓ Gmail connected ({self.gmail.email_address})")
            
            return True
            
        except Exception as e:
            print(f"✗ Initialization failed: {e}")
            return False
    
    def run(self):
        """Main loop - run until stopped."""
        if not self.initialize():
            print("Cannot start - initialization failed")
            return
        
        self.running = True
        self.current_poll_interval = self.poll_interval
        print(f"\nOrchestrator started. Polling every {self.poll_interval}s (dynamic)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                self._poll_cycle()
                print(f"  Next poll in {self.current_poll_interval}s")
                time.sleep(self.current_poll_interval)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self._save_state()
    
    def run_once(self, recheck_all: bool = False):
        """Run a single poll cycle (for cron/LaunchAgent). If recheck_all, re-evaluate every invite."""
        if not self.recall:
            if not self.initialize():
                return
        self._poll_cycle(recheck_all=recheck_all)
        self._save_state()
    
    def _get_dynamic_poll_interval(self) -> int:
        """Calculate polling interval based on upcoming meetings."""
        now = datetime.now()
        min_interval = 30  # Minimum 30 seconds
        default_interval = self.poll_interval
        
        # Check for imminent meetings
        for bot_id, info in self.active_bots.items():
            invite = info.get('invite', {})
            start_time = invite.get('start_time')
            
            if start_time and info.get('status') == 'created':
                try:
                    meeting_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    time_until = (meeting_dt - now).total_seconds()
                    
                    # Poll more frequently as meeting approaches
                    if time_until < 60:  # Less than 1 minute
                        return min_interval
                    elif time_until < 300:  # Less than 5 minutes
                        return 60
                    elif time_until < 600:  # Less than 10 minutes
                        return 120
                except:
                    pass
        
        return default_interval
    
    def _poll_cycle(self, recheck_all: bool = False):
        """One complete poll cycle."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling..." + (" (recheck all)" if recheck_all else ""))
        
        # Step 0: Clean up stale waiting-room or stuck bots from older runs.
        self._cleanup_stale_remote_bots()

        # Step 1: Check for completed bots
        self._check_completed_bots()

        # Step 1b: Notify if Gerald is stuck in waiting room.
        self._notify_waiting_room_bots()
        
        # Step 2: Check Gmail for new invites
        self._check_new_invites(recheck_all=recheck_all)
        
        # Step 3: Check for updated invites (reschedules)
        self._check_updated_invites()
        
        # Step 4: Save state
        self._save_state()
        
        # Update poll interval for next cycle
        self.current_poll_interval = self._get_dynamic_poll_interval()

    def _meeting_key_from_url(self, meeting_url: str) -> Optional[str]:
        if not meeting_url:
            return None
        if "meet.google.com/" in meeting_url:
            return "google_meet:" + meeting_url.rsplit("/", 1)[-1]
        return meeting_url

    def _meeting_key_from_bot(self, bot: Dict[str, Any]) -> Optional[str]:
        info = bot.get("meeting_url") or {}
        platform = info.get("platform")
        meeting_id = info.get("meeting_id")
        if platform and meeting_id:
            return f"{platform}:{meeting_id}"
        return None

    def _remote_bot_exists_for_meeting(self, meeting_url: str) -> bool:
        target = self._meeting_key_from_url(meeting_url)
        if not target:
            return False
        try:
            bots = self.recall.list_bots()
        except Exception:
            return False
        active_statuses = {"joining_call", "in_waiting_room", "in_lobby", "in_call", "recording"}
        for bot in bots:
            name = (bot.get("bot_name") or "").strip()
            if not name.startswith("Gerald"):
                continue
            status = (bot.get("status") or "").lower()
            if status not in active_statuses:
                continue
            if self._meeting_key_from_bot(bot) == target:
                return True
        return False

    def _parse_iso_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _cleanup_stale_remote_bots(self):
        """
        Ensure Gerald does not stay in a waiting room forever.

        Because launchd runs this script with --once, in-memory tracking resets each run.
        This pass inspects remote Recall bot state directly and exits stale bots.
        """
        try:
            bots = self.recall.list_bots()
        except Exception as e:
            print(f"Warning: could not list Recall bots for cleanup: {e}")
            return

        now = datetime.now().astimezone()
        stale_statuses = {"in_waiting_room", "joining_call", "in_lobby"}
        completed_statuses = {"done", "recording_done", "call_ended"}
        stale = []
        completed_meeting_keys = set()

        for bot in bots:
            bot_name = (bot.get("bot_name") or "").strip()
            if not bot_name.startswith("Gerald"):
                continue
            status = (bot.get("status") or "").strip().lower()
            if status not in completed_statuses:
                continue
            meeting_url = bot.get("meeting_url") or {}
            meeting_key = f"{meeting_url.get('platform')}:{meeting_url.get('meeting_id')}"
            completed_meeting_keys.add(meeting_key)

        for bot in bots:
            bot_name = (bot.get("bot_name") or "").strip()
            if not bot_name.startswith("Gerald"):
                continue

            status = (bot.get("status") or "").strip().lower()
            if status not in stale_statuses:
                continue

            meeting_url = bot.get("meeting_url") or {}
            meeting_key = f"{meeting_url.get('platform')}:{meeting_url.get('meeting_id')}"
            if meeting_key in completed_meeting_keys:
                # A completed Gerald bot already exists for this meeting.
                # Any waiting-room duplicate should be removed immediately.
                stale.append((bot, float("inf")))
                continue

            # Prefer join_at; fallback to last status_change timestamp.
            joined_at = self._parse_iso_datetime(bot.get("join_at"))
            if not joined_at:
                changes = bot.get("status_changes") or []
                if changes:
                    joined_at = self._parse_iso_datetime(changes[-1].get("created_at"))
            if not joined_at:
                continue

            age_min = (now - joined_at).total_seconds() / 60.0
            if age_min >= self.waiting_room_timeout_minutes:
                stale.append((bot, age_min))

        for bot, age_min in stale:
            bot_id = bot.get("id")
            status = bot.get("status")
            print(f"Stale bot cleanup: {bot_id[:8]}... status={status} age={age_min:.1f}m")

            # First ask it to leave; then attempt delete.
            try:
                if self.recall.leave_call(bot_id):
                    print("  ✓ leave_call sent")
                else:
                    print("  Warning: leave_call returned false")
            except Exception as e:
                print(f"  Warning: leave_call failed: {e}")

            try:
                # Give Recall a short moment to transition status.
                time.sleep(1)
                if self.recall.delete_bot(bot_id):
                    print("  ✓ deleted stale bot")
                else:
                    print("  Note: delete not allowed yet (will retry next cycle)")
            except Exception as e:
                print(f"  Warning: delete stale bot failed: {e}")
    
    def _check_updated_invites(self):
        """Check for updated calendar invites (reschedules)."""
        try:
            # Get recent invites (last hour)
            invites = self.gmail.get_calendar_invites(max_results=self.invite_scan_limit)
            
            for invite in invites:
                meeting_url = invite.get('meeting_url')
                msg_id = invite.get('message_id')
                
                if not meeting_url or not msg_id:
                    continue
                
                # Check if we have a bot for this URL with different message ID
                for bot_id, info in list(self.active_bots.items()):
                    existing_invite = info.get('invite', {})
                    if (existing_invite.get('meeting_url') == meeting_url and 
                        existing_invite.get('message_id') != msg_id):
                        
                        # This is an updated invite
                        print(f"Updated invite detected: {invite.get('subject', 'Unknown')}")
                        print(f"  Old time: {existing_invite.get('start_time')}")
                        print(f"  New time: {invite.get('start_time')}")
                        
                        # Remove old bot
                        del self.active_bots[bot_id]
                        if meeting_url in self.scheduled_meetings:
                            del self.scheduled_meetings[meeting_url]
                        
                        # Process as new invite
                        if self._should_join_meeting(invite):
                            self._schedule_bot(invite)
                        
                        break
                        
        except Exception as e:
            print(f"Error checking updated invites: {e}")
    
    def _check_new_invites(self, recheck_all: bool = False):
        """Check Gmail for new calendar invites. If recheck_all, re-evaluate every invite (e.g. to join a meeting that was skipped)."""
        try:
            invites = self.gmail.get_calendar_invites(max_results=self.invite_scan_limit)
            
            new_invites = 0
            for invite in invites:
                msg_id = invite.get('message_id')
                
                # Skip already processed (unless recheck_all)
                if not recheck_all and msg_id in self.processed_invites:
                    continue
                
                meeting_url = invite.get('meeting_url')
                if not meeting_url:
                    continue
                
                if not recheck_all:
                    print(f"New invite: {invite.get('subject', 'Unknown')}")
                else:
                    print(f"Recheck invite: {invite.get('subject', 'Unknown')}")
                print(f"  URL: {meeting_url}")
                
                # Check if we should join this meeting
                should_join = self._should_join_meeting(invite)
                if should_join:
                    self._schedule_bot(invite)
                # Mark as processed only when we don't need to re-check: we joined, meeting ended, or we already have a bot for this invite
                already_has_bot = any(
                    info.get('invite', {}).get('message_id') == msg_id
                    for info in self.active_bots.values()
                )
                if should_join or self._invite_already_ended(invite) or already_has_bot:
                    self.processed_invites.add(msg_id)
                new_invites += 1
            
            if new_invites > 0:
                print(f"Processed {new_invites} new invites")
                
        except Exception as e:
            print(f"Error checking invites: {e}")
    
    def _invite_already_ended(self, invite: Dict[str, Any]) -> bool:
        """True if meeting has ended (so we can mark as processed and stop re-checking)."""
        end_time = invite.get('end_time') or invite.get('start_time')
        if not end_time:
            return False
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            now = datetime.now(end_dt.tzinfo)
            return now > end_dt
        except Exception:
            return False

    def _should_join_meeting(self, invite: Dict[str, Any]) -> bool:
        """
        Determine if we should join a meeting.
        
        Criteria:
        - Meeting is happening now or in the next 30 minutes
        - Not already scheduled
        - Not a declined invite
        - Updated invites (same URL, new time) should be re-evaluated
        """
        meeting_url = invite.get('meeting_url')
        msg_id = invite.get('message_id')
        
        # Check if this is an updated invite (same URL, different message ID)
        existing_bot = None
        for bot_id, info in self.active_bots.items():
            if info.get('invite', {}).get('meeting_url') == meeting_url:
                existing_bot = info
                break
        
        # If we already have a bot for this URL, check if it's the same invite
        if existing_bot:
            existing_msg_id = existing_bot.get('invite', {}).get('message_id')
            if existing_msg_id == msg_id:
                # Same invite, already processed
                return False
            else:
                # Different message ID = updated invite (rescheduled)
                print(f"  Detected updated invite (rescheduled meeting)")
                # Remove old bot tracking
                old_bot_id = None
                for bid, info in self.active_bots.items():
                    if info.get('invite', {}).get('meeting_url') == meeting_url:
                        old_bot_id = bid
                        break
                if old_bot_id:
                    try:
                        self.recall.delete_bot(old_bot_id)
                        print(f"  Deleted replaced bot {old_bot_id[:8]}... (reschedule)")
                    except Exception as e:
                        print(f"  Warning: could not delete old bot: {e}")
                    del self.active_bots[old_bot_id]
                if meeting_url in self.scheduled_meetings:
                    del self.scheduled_meetings[meeting_url]
        
        # Check start time if available
        start_time = invite.get('start_time')
        end_time = invite.get('end_time')
        if start_time:
            try:
                # Parse ISO format time
                meeting_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                now = datetime.now(meeting_dt.tzinfo)
                
                # Check if meeting has ended
                if end_time:
                    try:
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        if now > end_dt:
                            print(f"  Skipping - meeting already ended")
                            return False
                    except:
                        pass
                
                # Only join when meeting is within window (avoids runaway joins; configurable)
                # RECALL_JOIN_WINDOW_MINUTES = how many min before start we create bot (default 15); RECALL_JOIN_GRACE_MINUTES = how long after start we still join (default 5)
                window_min = int(os.environ.get("RECALL_JOIN_WINDOW_MINUTES", "15"))
                grace_min = int(os.environ.get("RECALL_JOIN_GRACE_MINUTES", "5"))
                window_sec = window_min * 60
                grace_sec = -grace_min * 60
                time_diff = (meeting_dt - now).total_seconds()
                
                if time_diff > window_sec:
                    print(f"  Skipping - starts in {time_diff/60:.0f} min (window={window_min} min)")
                    return False
                elif time_diff < grace_sec:
                    print(f"  Skipping - started {abs(time_diff)/60:.0f} min ago (grace={grace_min} min)")
                    return False
                else:
                    if time_diff < 0:
                        print(f"  Joining - meeting started {abs(time_diff)/60:.0f} min ago")
                    else:
                        print(f"  Joining - meeting starts in {time_diff/60:.0f} min")
                    return True
                    
            except Exception as e:
                print(f"  Warning: Could not parse meeting time: {e}")
                return False
        
        # No start_time or could not parse: do NOT join (was wrongly defaulting to True and joining everything)
        print(f"  Skipping - no valid start_time in invite")
        return False
    
    def _schedule_bot(self, invite: Dict[str, Any]):
        """Schedule a Recall.ai bot to join a meeting. (Set RECALL_JOIN_ENABLED=false only to pause joining, e.g. vacation.)"""
        if os.environ.get("RECALL_JOIN_ENABLED", "true").lower() in ("0", "false", "no", "off"):
            print("  Skipping - RECALL_JOIN_ENABLED is off")
            return
        meeting_url = invite.get('meeting_url')
        subject = invite.get('subject', 'Meeting')

        if self._remote_bot_exists_for_meeting(meeting_url):
            print("  Skipping - active Gerald bot already exists for this meeting")
            return
        
        try:
            # Create bot immediately (Recall.ai handles joining at right time)
            bot = self.recall.create_bot(
                meeting_url=meeting_url,
                name="Gerald (Notetaker)"
            )
            
            bot_id = bot.get('id')
            print(f"  Bot created: {bot_id}")
            
            # Track it
            self.active_bots[bot_id] = {
                'invite': invite,
                'bot': bot,
                'created_at': datetime.now().isoformat(),
                'status': 'created'
            }
            
            self.scheduled_meetings[meeting_url] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"  Error creating bot: {e}")

    def _notify_waiting_room_bots(self):
        """
        Alert Jason when Gerald is stuck in waiting room long enough to need admission.
        """
        try:
            bots = self.recall.list_bots()
        except Exception as e:
            print(f"Warning: could not list bots for waiting room alert: {e}")
            return

        now = datetime.now().astimezone()
        active_bot_ids = set()

        for bot in bots:
            bot_id = bot.get("id")
            bot_name = (bot.get("bot_name") or "").strip()
            if not bot_id or not bot_name.startswith("Gerald"):
                continue

            status = (bot.get("status") or "").lower()
            if status == "in_waiting_room":
                active_bot_ids.add(bot_id)
                joined_at = self._parse_iso_datetime(bot.get("join_at"))
                if not joined_at:
                    changes = bot.get("status_changes") or []
                    if changes:
                        joined_at = self._parse_iso_datetime(changes[-1].get("created_at"))
                if not joined_at:
                    continue

                age_min = (now - joined_at).total_seconds() / 60.0
                if age_min >= self.waiting_room_alert_minutes and bot_id not in self.waiting_room_alerted_bots:
                    meeting_key = self._meeting_key_from_bot(bot) or "unknown meeting"
                    msg = (
                        "⚠️ Gerald is waiting in a meeting room.\n"
                        f"- Meeting: {meeting_key}\n"
                        f"- Waiting: {age_min:.0f} minutes\n"
                        "Please admit Gerald in Google Meet."
                    )
                    if sessions_send(self.alert_telegram_chat_id, msg):
                        self.waiting_room_alerted_bots.add(bot_id)
                        print(f"  Sent waiting-room alert for bot {bot_id[:8]}...")

            elif status in {"done", "left", "failed", "kicked"}:
                # If a bot is no longer waiting, clear notification marker.
                if bot_id in self.waiting_room_alerted_bots:
                    self.waiting_room_alerted_bots.discard(bot_id)

        # Safety prune: remove alert markers for bots no longer present.
        self.waiting_room_alerted_bots = {
            bot_id for bot_id in self.waiting_room_alerted_bots if bot_id in active_bot_ids
        }
    
    def _check_completed_bots(self):
        """Check if any bots have completed and process transcripts."""
        completed_bots = []
        
        for bot_id, info in self.active_bots.items():
            try:
                # Check status
                bot = self.recall.get_bot(bot_id)
                status = bot.get('status')
                
                if status != info.get('status'):
                    print(f"Bot {bot_id[:8]}... status: {status}")
                    info['status'] = status
                
                if status == 'done':
                    completed_bots.append(bot_id)
                elif status in ['failed', 'kicked', 'left']:
                    print(f"  Bot ended with status: {status}")
                    completed_bots.append(bot_id)
                    
            except Exception as e:
                print(f"Error checking bot {bot_id}: {e}")
        
        # Process completed bots
        for bot_id in completed_bots:
            self._process_completed_bot(bot_id)
    
    def _process_completed_bot(self, bot_id: str):
        """Process a completed bot's transcript, then delete bot on Recall to free concurrent limit."""
        info = self.active_bots.get(bot_id)
        if not info:
            return
        
        print(f"\nProcessing completed bot: {bot_id[:8]}...")
        
        try:
            # Get transcript
            transcript = self.recall.get_transcript(bot_id)
            
            if transcript:
                print(f"  Retrieved transcript ({len(transcript)} segments)")
                meeting_info = info.get('invite', {})
                analysis = self.processor.process_transcript(transcript, meeting_info)
                filepath = self.processor.save_analysis(analysis, self.meetings_dir)
                print(f"  Saved analysis to: {filepath}")
                try:
                    self._send_meeting_summary(analysis, filepath)
                except Exception as e:
                    print(f"  Warning: Could not send email: {e}")
                info['processed'] = True
                info['analysis_file'] = filepath
            else:
                print("  No transcript available")
        except Exception as e:
            print(f"  Error processing transcript: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Always delete bot on Recall to free the concurrent bot limit (30)
            try:
                if self.recall.delete_bot(bot_id):
                    print(f"  ✓ Deleted bot on Recall (freed slot)")
                else:
                    print(f"  Warning: could not delete bot on Recall")
            except Exception as e:
                print(f"  Warning: could not delete bot on Recall: {e}")
            if bot_id in self.active_bots:
                del self.active_bots[bot_id]
    
    def _send_meeting_summary(self, analysis: Dict[str, Any], filepath: str):
        """Send meeting summary via email."""
        from gmail_client import GmailClient
        
        # Build email content
        subject = analysis.get('subject', 'Meeting Summary')
        meeting_date = analysis.get('date', 'Unknown date')
        subject_line = f"Meeting Summary: {subject} - {meeting_date}"
        
        # Helper to safely convert to string
        def safe_str(value, default=''):
            if value is None:
                return default
            if isinstance(value, dict):
                return str(value)
            if isinstance(value, list):
                return ', '.join(str(x) for x in value)
            return str(value)
        
        # Build body
        body_lines = [
            f"# Meeting Summary: {safe_str(subject)}",
            f"",
            f"**Date:** {safe_str(meeting_date)}",
            f"**Duration:** {safe_str(analysis.get('duration', 'Unknown'))}",
            f"**Participants:** {', '.join(safe_str(p) for p in analysis.get('participants', ['Unknown']))}",
            f"",
            f"## Summary",
            f"",
            safe_str(analysis.get('summary', 'No summary available.')),
            f"",
        ]
        
        # Add action items
        action_items = analysis.get('action_items', [])
        if action_items:
            body_lines.extend([
                f"## Action Items",
                f"",
            ])
            for item in action_items:
                if isinstance(item, dict):
                    assignee = safe_str(item.get('assignee', 'Unassigned'))
                    text = safe_str(item.get('text', ''))
                    body_lines.append(f"- [ ] {text} (@{assignee})")
                else:
                    body_lines.append(f"- [ ] {safe_str(item)}")
            body_lines.append(f"")
        
        # Add customer mentions
        customers = analysis.get('customers', [])
        if customers:
            body_lines.extend([
                f"## Customer Mentions",
                f"",
            ])
            for customer in customers:
                if isinstance(customer, dict):
                    name = safe_str(customer.get('name', 'Unknown'))
                    mentions = customer.get('mentions', [])
                    body_lines.append(f"- **{name}**: {len(mentions)} mention(s)")
                else:
                    body_lines.append(f"- {safe_str(customer)}")
            body_lines.append(f"")
        
        # Add full transcript link
        body_lines.extend([
            f"---",
            f"*Full analysis saved to: {safe_str(filepath)}*",
            f"*Generated by Gerald - OpenClaw Meeting Assistant*",
        ])
        
        body = '\n'.join(body_lines)
        
        # Send email
        gmail = GmailClient()
        # Meeting summary delivery requires gmail.send scope.
        if gmail.authenticate_with_send():
            gmail.send_email(
                to="jason@allgreatthings.io",
                subject=subject_line,
                body=body
            )
            print(f"  ✓ Email sent to jason@allgreatthings.io")
            self._log_meeting_to_daily_memory(analysis)
        else:
            print(f"  ✗ Could not authenticate Gmail")

    def _log_meeting_to_daily_memory(self, analysis: Dict[str, Any]):
        """Append one line to memory/YYYY-MM-DD.md so Gerald (the agent) sees his meeting in his daily read."""
        try:
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            subject = analysis.get('subject', 'Meeting')
            path = os.path.join(os.path.dirname(self.meetings_dir), f"{today}.md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            line = f"- **Meetings:** Attended \"{subject}\"; summary emailed to jason@allgreatthings.io.\n"
            with open(path, "a") as f:
                f.write(line)
        except Exception as e:
            print(f"  Warning: could not log to daily memory: {e}")
    
    def _load_state(self):
        """Load persistent state from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                self.processed_invites = set(state.get('processed_invites', []))
                self.scheduled_meetings = state.get('scheduled_meetings', {})
                self.waiting_room_alerted_bots = set(state.get('waiting_room_alerted_bots', []))
                self.active_bots = state.get('active_bots', {})
                
                print(f"Loaded state: {len(self.processed_invites)} processed invites")
            except Exception as e:
                print(f"Warning: Could not load state: {e}")
    
    def _save_state(self):
        """Save persistent state to disk."""
        state = {
            'last_saved': datetime.now().isoformat(),
            'processed_invites': list(self.processed_invites),
            'scheduled_meetings': self.scheduled_meetings,
            'waiting_room_alerted_bots': list(self.waiting_room_alerted_bots),
            'active_bots': self.active_bots,
        }
        
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")


def main():
    """Main entry point."""
    import sys
    if "--gmail-auth-only" in sys.argv:
        # Complete Gmail OAuth only (no Recall). Use when Recall key is not yet valid.
        print("Gmail OAuth only — completing first-time sign-in...")
        try:
            gmail = GmailClient()
            if gmail.authenticate():
                print(f"✓ Gmail connected ({gmail.email_address})")
                print("Token saved to credentials/gmail-token.pickle")
            else:
                print("✗ Gmail authentication failed")
                sys.exit(1)
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)
        return

    orchestrator = MeetingOrchestrator()
    if "--once" in sys.argv:
        # Single poll cycle then exit (for cron/LaunchAgent). --recheck re-evaluates all invites.
        recheck = "--recheck" in sys.argv
        orchestrator.run_once(recheck_all=recheck)
        return
    orchestrator.run()


if __name__ == "__main__":
    main()
