#!/usr/bin/env python3
"""
Master Scheduler for OpenClaw Automations
Runs all scheduled tasks based on time/day.

Usage:
  python3 tools/scheduler.py  # Run scheduled tasks for current time
  
Add to crontab:
  0 9 * * * cd /Users/jcore/Desktop/Openclaw && python3 tools/scheduler.py
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Schedule configuration
SCHEDULE = {
    # Daily at 8:30am - collect data for 9am digest
    'daily_830am': {
        'time': (8, 30),
        'tasks': [
            ('X Monitor', 'tools/x_multi_monitor.py', ['--once']),
            ('Task Reminders', 'tools/task_reminder.py', ['--check']),
        ]
    },
    # Daily at 9am - send digest (always sends, even if empty)
    'daily_9am': {
        'time': (9, 0),
        'tasks': [
            ('Daily Digest', 'tools/daily_digest.py', []),
        ]
    },
    # Daily at 6pm
    'daily_6pm': {
        'time': (18, 0),
        'tasks': [
            ('X Monitor Evening', 'tools/x_multi_monitor.py', ['--once']),
        ]
    },
    # Monday 9am (weekly)
    'weekly_monday': {
        'day': 0,  # Monday
        'time': (9, 0),
        'tasks': [
            ('Security Review', 'tools/security_review.py', ['--email']),
        ]
    }
}


def run_task(name, script, args):
    """Run a scheduled task."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")
    
    cmd = [sys.executable, script] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {name}: {e}")
        return False


def should_run(schedule_key, now):
    """Check if a schedule should run at current time."""
    config = SCHEDULE[schedule_key]
    target_time = config['time']
    
    # Check time match (within 5 minute window)
    time_match = (now.hour == target_time[0] and now.minute <= 5)
    
    # Check day match if specified
    if 'day' in config:
        day_match = now.weekday() == config['day']
        return time_match and day_match
    
    return time_match


def main():
    now = datetime.now()
    print(f"Scheduler running at {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    
    ran_any = False
    
    for schedule_key, config in SCHEDULE.items():
        if should_run(schedule_key, now):
            print(f"\n📅 Schedule triggered: {schedule_key}")
            
            for task_name, script, args in config['tasks']:
                success = run_task(task_name, script, args)
                status = "✓" if success else "✗"
                print(f"{status} {task_name}")
                ran_any = True
    
    if not ran_any:
        print("\nNo schedules triggered at this time.")
        print("Scheduled times:")
        for key, config in SCHEDULE.items():
            time_str = f"{config['time'][0]:02d}:{config['time'][1]:02d}"
            if 'day' in config:
                days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                print(f"  {key}: {days[config['day']]} @ {time_str}")
            else:
                print(f"  {key}: Daily @ {time_str}")


if __name__ == '__main__':
    main()
