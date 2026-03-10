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
        
        # Clients
        self.recall = None
        self.gmail = None
        self.processor = MeetingProcessor()
        
        # State
        self.running = False
        self.processed_invites = set()
        self.active_bots = {}  # bot_id -> meeting_info
        self.scheduled_meetings = {}  # meeting_url -> scheduled_time
        
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
    
    def run_once(self):
        """Run a single poll cycle (for testing)."""
        if not self.recall:
            if not self.initialize():
                return
        
        self._poll_cycle()
    
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
    
    def _poll_cycle(self):
        """One complete poll cycle."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling...")
        
        # Step 1: Check for completed bots
        self._check_completed_bots()
        
        # Step 2: Check Gmail for new invites
        self._check_new_invites()
        
        # Step 3: Check for updated invites (reschedules)
        self._check_updated_invites()
        
        # Step 4: Save state
        self._save_state()
        
        # Update poll interval for next cycle
        self.current_poll_interval = self._get_dynamic_poll_interval()
    
    def _check_updated_invites(self):
        """Check for updated calendar invites (reschedules)."""
        try:
            # Get recent invites (last hour)
            invites = self.gmail.get_calendar_invites(max_results=50)
            
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
    
    def _check_new_invites(self):
        """Check Gmail for new calendar invites."""
        try:
            invites = self.gmail.get_calendar_invites(max_results=20)
            
            new_invites = 0
            for invite in invites:
                msg_id = invite.get('message_id')
                
                # Skip already processed
                if msg_id in self.processed_invites:
                    continue
                
                meeting_url = invite.get('meeting_url')
                if not meeting_url:
                    continue
                
                print(f"New invite: {invite.get('subject', 'Unknown')}")
                print(f"  URL: {meeting_url}")
                
                # Check if we should join this meeting
                if self._should_join_meeting(invite):
                    self._schedule_bot(invite)
                
                self.processed_invites.add(msg_id)
                new_invites += 1
            
            if new_invites > 0:
                print(f"Processed {new_invites} new invites")
                
        except Exception as e:
            print(f"Error checking invites: {e}")
    
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
                
                # Join if meeting is happening now or within next 30 minutes
                # Or if it started up to 15 minutes ago (for delayed starts/reschedules)
                time_diff = (meeting_dt - now).total_seconds()
                
                if time_diff > 1800:  # More than 30 minutes in future
                    print(f"  Scheduling for later (starts in {time_diff/60:.0f} minutes)")
                    return False
                elif time_diff < -900:  # More than 15 minutes ago
                    print(f"  Skipping - meeting started {abs(time_diff)/60:.0f} minutes ago")
                    return False
                else:
                    # Meeting is now, upcoming soon, or recently started
                    if time_diff < 0:
                        print(f"  Joining - meeting already started ({abs(time_diff)/60:.0f} min ago)")
                    else:
                        print(f"  Joining - meeting starts in {time_diff/60:.0f} minutes")
                    return True
                    
            except Exception as e:
                print(f"  Warning: Could not parse meeting time: {e}")
        
        return True
    
    def _schedule_bot(self, invite: Dict[str, Any]):
        """Schedule a Recall.ai bot to join a meeting."""
        meeting_url = invite.get('meeting_url')
        subject = invite.get('subject', 'Meeting')
        
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
        """Process a completed bot's transcript."""
        info = self.active_bots.get(bot_id)
        if not info:
            return
        
        print(f"\nProcessing completed bot: {bot_id[:8]}...")
        
        try:
            # Get transcript
            transcript = self.recall.get_transcript(bot_id)
            
            if not transcript:
                print("  No transcript available")
                return
            
            print(f"  Retrieved transcript ({len(transcript)} segments)")
            
            # Process
            meeting_info = info.get('invite', {})
            analysis = self.processor.process_transcript(transcript, meeting_info)
            
            # Save
            filepath = self.processor.save_analysis(analysis, self.meetings_dir)
            print(f"  Saved analysis to: {filepath}")
            
            # Send email summary
            try:
                self._send_meeting_summary(analysis, filepath)
            except Exception as e:
                print(f"  Warning: Could not send email: {e}")
            
            # Cleanup
            info['processed'] = True
            info['analysis_file'] = filepath
            
        except Exception as e:
            print(f"  Error processing transcript: {e}")
            import traceback
            traceback.print_exc()
    
    def _send_meeting_summary(self, analysis: Dict[str, Any], filepath: str):
        """Send meeting summary via email."""
        from gmail_client import GmailClient
        
        # Build email content
        subject = analysis.get('subject', 'Meeting Summary')
        meeting_date = analysis.get('date', 'Unknown date')
        subject_line = f"Meeting Summary: {subject} - {meeting_date}"
        
        # Build body
        body_lines = [
            f"# Meeting Summary: {subject}",
            f"",
            f"**Date:** {meeting_date}",
            f"**Duration:** {analysis.get('duration', 'Unknown')}",
            f"**Participants:** {', '.join(analysis.get('participants', ['Unknown']))}",
            f"",
            f"## Summary",
            f"",
            analysis.get('summary', 'No summary available.'),
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
                assignee = item.get('assignee', 'Unassigned')
                text = item.get('text', '')
                body_lines.append(f"- [ ] {text} (@{assignee})")
            body_lines.append(f"")
        
        # Add customer mentions
        customers = analysis.get('customers', [])
        if customers:
            body_lines.extend([
                f"## Customer Mentions",
                f"",
            ])
            for customer in customers:
                name = customer.get('name', 'Unknown')
                mentions = customer.get('mentions', [])
                body_lines.append(f"- **{name}**: {len(mentions)} mention(s)")
            body_lines.append(f"")
        
        # Add full transcript link
        body_lines.extend([
            f"---",
            f"*Full analysis saved to: {filepath}*",
            f"*Generated by Gerald - OpenClaw Meeting Assistant*",
        ])
        
        body = '\n'.join(body_lines)
        
        # Send email
        gmail = GmailClient()
        if gmail.authenticate():
            gmail.send_email(
                to="jason@allgreatthings.io",
                subject=subject_line,
                body=body
            )
            print(f"  ✓ Email sent to jason@allgreatthings.io")
        else:
            print(f"  ✗ Could not authenticate Gmail")
    
    def _load_state(self):
        """Load persistent state from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                self.processed_invites = set(state.get('processed_invites', []))
                self.scheduled_meetings = state.get('scheduled_meetings', {})
                
                print(f"Loaded state: {len(self.processed_invites)} processed invites")
            except Exception as e:
                print(f"Warning: Could not load state: {e}")
    
    def _save_state(self):
        """Save persistent state to disk."""
        state = {
            'last_saved': datetime.now().isoformat(),
            'processed_invites': list(self.processed_invites),
            'scheduled_meetings': self.scheduled_meetings,
            'active_bots': {k: {
                'status': v.get('status'),
                'created_at': v.get('created_at'),
                'processed': v.get('processed', False)
            } for k, v in self.active_bots.items()}
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
    orchestrator.run()


if __name__ == "__main__":
    main()
