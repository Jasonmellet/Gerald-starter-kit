#!/usr/bin/env python3
"""
Task Reminder System for OpenClaw
Checks TASKS.md for deadlines and triggers actions.

Usage:
  python3 tools/task_reminder.py --check       # Check for due tasks
  python3 tools/task_reminder.py --list        # List all tasks with deadlines
  python3 tools/task_reminder.py --complete "Task name"  # Mark task complete

Stores state in memory/task-reminders.json
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

TASKS_FILE = Path(__file__).resolve().parent.parent / "TASKS.md"
STATE_FILE = Path(__file__).resolve().parent.parent / "memory" / "task-reminders.json"


def parse_tasks() -> List[Dict[str, Any]]:
    """Parse TASKS.md and extract tasks with deadlines."""
    if not TASKS_FILE.exists():
        return []
    
    content = TASKS_FILE.read_text()
    tasks = []
    
    # Parse Active Tasks section
    active_section = re.search(r'## Active Tasks\n\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if active_section:
        section_content = active_section.group(1)
        
        # Find each task (bullet points starting with - **)
        task_blocks = re.findall(r'- \*\*(.*?)\*\* — (.*?)(?=\n- \*\*|\Z)', section_content, re.DOTALL)
        
        for name, details in task_blocks:
            task = {
                'name': name.strip(),
                'details': details.strip().replace('\n  ', ' '),
                'deadline': None,
                'action': None,
                'section': 'Active'
            }
            
            # Extract deadline patterns:
            # "Send reminder Monday 8am CST"
            # "Due: 2026-03-10"
            # "Deadline: March 10, 2026"
            
            deadline_patterns = [
                r'Send reminder\s+(.+?)(?:\.|$)',
                r'Due[:\s]+(.+?)(?:\.|$)',
                r'Deadline[:\s]+(.+?)(?:\.|$)',
                r'by\s+(.+?)(?:\.|$)'
            ]
            
            for pattern in deadline_patterns:
                match = re.search(pattern, task['details'], re.IGNORECASE)
                if match:
                    task['deadline_str'] = match.group(1).strip()
                    task['deadline'] = parse_deadline(task['deadline_str'])
                    break
            
            # Extract action (email, reminder, etc.)
            if 'email' in task['details'].lower():
                task['action'] = 'email'
                # Extract email address
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', task['details'])
                if email_match:
                    task['email_to'] = email_match.group(0)
            elif 'remind' in task['details'].lower():
                task['action'] = 'remind'
            
            tasks.append(task)
    
    return tasks


def parse_deadline(deadline_str: str, created_date: Optional[datetime] = None) -> Optional[datetime]:
    """Parse various deadline formats into datetime."""
    now = datetime.now()
    deadline_str = deadline_str.lower().strip()
    
    # Handle "Monday 8am CST" format
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for i, day in enumerate(days):
        if day in deadline_str:
            # Find occurrence of this day
            current_day = now.weekday()
            target_day = i
            days_ahead = (target_day - current_day) % 7
            
            # If "next" is specified, always use next week
            if 'next' in deadline_str:
                if days_ahead == 0:
                    days_ahead = 7
            # If we're parsing a deadline from a task created in the past,
            # and the day has already passed this week, assume it was last occurrence
            elif created_date and days_ahead == 0:
                # Same day as today - check if time has passed
                pass
            
            target_date = now + timedelta(days=days_ahead)
            
            # Parse time if present
            time_match = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)?', deadline_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                ampm = time_match.group(3)
                
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                
                target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
            return target_date
    
    # Handle "tomorrow" format
    if 'tomorrow' in deadline_str:
        target_date = now + timedelta(days=1)
        target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        return target_date
    
    # Handle date formats: 2026-03-10, March 10 2026, etc.
    date_patterns = [
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, deadline_str)
        if match:
            try:
                if pattern.startswith(r'(\d{4})'):
                    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                else:
                    month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                return datetime(year, month, day, 9, 0, 0)
            except:
                pass
    
    return None


def load_state() -> Dict:
    """Load reminder state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        'completed': [],
        'snoozed': {},
        'last_check': None
    }


def save_state(state: Dict):
    """Save reminder state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def check_due_tasks(tasks: List[Dict], state: Dict) -> List[Dict]:
    """Check for tasks that are due."""
    now = datetime.now()
    due_tasks = []
    
    for task in tasks:
        # Skip completed tasks
        if task['name'] in state.get('completed', []):
            continue
        
        # Skip snoozed tasks
        snooze_until = state.get('snoozed', {}).get(task['name'])
        if snooze_until:
            snooze_time = datetime.fromisoformat(snooze_until)
            if now < snooze_time:
                continue
        
        # Check if deadline has passed
        if task.get('deadline'):
            if now >= task['deadline']:
                due_tasks.append(task)
    
    return due_tasks


def execute_task_action(task: Dict) -> bool:
    """Execute the action for a due task."""
    action = task.get('action')
    
    if action == 'email' and task.get('email_to'):
        # Import here to avoid circular imports
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from gmail_client import GmailClient
        
        try:
            gmail = GmailClient()
            if gmail.authenticate():
                # Extract subject from task details
                subject = f"Reminder: {task['name']}"
                
                # Build body
                body_lines = [
                    f"Hi there,",
                    f"",
                    f"This is an automated reminder from Gerald (Jason's AI assistant).",
                    f"",
                    f"Task: {task['name']}",
                    f"Details: {task['details']}",
                    f"",
                    f"If you need help with this, please reply or contact Jason.",
                    f"",
                    f"Thanks!",
                    f"Gerald"
                ]
                
                gmail.send_email(
                    to=task['email_to'],
                    subject=subject,
                    body='\n'.join(body_lines)
                )
                print(f"  ✓ Email sent to {task['email_to']}")
                return True
        except Exception as e:
            print(f"  ✗ Failed to send email: {e}")
            return False
    
    elif action == 'remind':
        print(f"  ⚠️ REMINDER: {task['name']}")
        print(f"     {task['details']}")
        return True
    
    else:
        print(f"  ⚠️ TASK DUE: {task['name']}")
        print(f"     {task['details']}")
        return True


def mark_complete(task_name: str, state: Dict):
    """Mark a task as completed."""
    if task_name not in state.get('completed', []):
        state.setdefault('completed', []).append(task_name)
        save_state(state)
        print(f"✓ Marked '{task_name}' as complete")


def main():
    parser = argparse.ArgumentParser(description='Task Reminder System')
    parser.add_argument('--check', action='store_true', help='Check for due tasks')
    parser.add_argument('--list', action='store_true', help='List all tasks with deadlines')
    parser.add_argument('--complete', metavar='TASK_NAME', help='Mark a task as complete')
    
    args = parser.parse_args()
    
    if args.complete:
        state = load_state()
        mark_complete(args.complete, state)
        return
    
    tasks = parse_tasks()
    state = load_state()
    
    if args.list:
        print("Tasks with deadlines:")
        print("=" * 60)
        for task in tasks:
            status = "✓ Complete" if task['name'] in state.get('completed', []) else "⏳ Pending"
            deadline = task.get('deadline_str', 'No deadline')
            if task.get('deadline'):
                deadline += f" ({task['deadline'].strftime('%Y-%m-%d %H:%M')})"
            print(f"\n{status} {task['name']}")
            print(f"  Deadline: {deadline}")
            print(f"  Action: {task.get('action', 'None')}")
        return
    
    if args.check:
        print("Checking for due tasks...")
        due_tasks = check_due_tasks(tasks, state)
        
        if not due_tasks:
            print("No tasks due.")
            return
        
        print(f"\nFound {len(due_tasks)} due task(s):")
        print("=" * 60)
        
        for task in due_tasks:
            print(f"\n🚨 {task['name']}")
            print(f"   Deadline: {task.get('deadline_str', 'Unknown')}")
            success = execute_task_action(task)
            
            if success and task.get('action') == 'email':
                # Mark as complete after successful email
                mark_complete(task['name'], state)
        
        # Update last check time
        state['last_check'] = datetime.now().isoformat()
        save_state(state)


if __name__ == '__main__':
    main()
