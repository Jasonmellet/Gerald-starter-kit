#!/usr/bin/env python3
"""
Scheduled Reports System
Generates and sends automated security and activity reports.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from logger import log_conversation, log_action
from send_email import send_email
from bouncer import get_bouncer

REPORTS_DIR = Path("memory/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ReportGenerator:
    """Generates various scheduled reports."""
    
    def __init__(self):
        self.db_path = Path("memory/gerald_logs.db")
    
    def generate_daily_summary(self) -> str:
        """Generate daily activity summary."""
        report = []
        report.append("📊 DAILY ACTIVITY SUMMARY")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 60)
        report.append("")
        
        # Get bouncer stats
        from bouncer import get_bouncer
        bouncer_stats = get_bouncer().get_stats()
        
        report.append("🥊 BOUNCER ACTIVITY")
        report.append("-" * 40)
        report.append(f"Operations blocked today: {bouncer_stats['total_blocked']}")
        if bouncer_stats['blocked_by_type']:
            for op_type, count in bouncer_stats['blocked_by_type'].items():
                report.append(f"  - {op_type}: {count}")
        report.append("")
        
        # Get API spending
        spending_file = Path("memory/api-usage/spending.json")
        if spending_file.exists():
            with open(spending_file, 'r') as f:
                data = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            day_data = data.get('by_day', {}).get(today, {'spent': 0.0, 'calls': 0})
            
            report.append("💰 API SPENDING")
            report.append("-" * 40)
            report.append(f"Today: ${day_data.get('spent', 0):.2f}")
            report.append(f"Calls: {day_data.get('calls', 0)}")
            report.append(f"Month total: ${data.get('total_spent', 0):.2f}")
            report.append("")
        
        # Get security alerts
        alerts_file = Path("memory/security/alerts.json")
        if alerts_file.exists():
            with open(alerts_file, 'r') as f:
                alerts = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            today_alerts = [a for a in alerts if a['timestamp'].startswith(today)]
            
            if today_alerts:
                report.append("⚠️ SECURITY ALERTS TODAY")
                report.append("-" * 40)
                for alert in today_alerts:
                    emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
                    report.append(f"{emoji.get(alert['level'], '⚠️')} [{alert['level']}] {alert['category']}")
                    report.append(f"   {alert['message'][:60]}")
                report.append("")
            else:
                report.append("✅ No security alerts today")
                report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def generate_critical_alert(self, alert_data: dict) -> str:
        """Generate immediate critical alert."""
        report = []
        report.append("🔴 CRITICAL SECURITY ALERT")
        report.append("=" * 60)
        report.append(f"Time: {datetime.now().isoformat()}")
        report.append(f"Category: {alert_data.get('category', 'UNKNOWN')}")
        report.append(f"Level: {alert_data.get('level', 'CRITICAL')}")
        report.append("")
        report.append(f"MESSAGE:")
        report.append(f"{alert_data.get('message', 'No message')}")
        report.append("")
        
        if alert_data.get('details'):
            report.append("DETAILS:")
            report.append(json.dumps(alert_data.get('details'), indent=2))
        
        report.append("")
        report.append("=" * 60)
        report.append("Immediate action recommended.")
        report.append("Run: python3 tools/cso.py --status")
        
        return "\n".join(report)
    
    def send_daily_report(self, to: str = "jason@allgreatthings.io"):
        """Generate and send daily summary."""
        report = self.generate_daily_summary()
        
        # Save to file
        report_file = REPORTS_DIR / f"daily_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        # Send email
        subject = f"📊 Daily Security Summary - {datetime.now().strftime('%b %d, %Y')}"
        
        try:
            send_email(to=to, subject=subject, body=report)
            print(f"✓ Daily report sent to {to}")
            print(f"  Saved to: {report_file}")
        except Exception as e:
            print(f"✗ Failed to send daily report: {e}")
    
    def send_critical_alert(self, alert_data: dict, to: str = "jason@allgreatthings.io"):
        """Send immediate critical alert."""
        report = self.generate_critical_alert(alert_data)
        
        subject = f"🔴 CRITICAL: {alert_data.get('category', 'Security Alert')} - Immediate Action Required"
        
        try:
            send_email(to=to, subject=subject, body=report)
            print(f"✓ Critical alert sent to {to}")
        except Exception as e:
            print(f"✗ Failed to send critical alert: {e}")
    
    def generate_weekly_digest(self) -> str:
        """Generate comprehensive weekly report."""
        report = []
        report.append("📋 WEEKLY SECURITY & ACTIVITY DIGEST")
        report.append(f"Week of: {datetime.now().strftime('%Y-%m-%d')}")
        report.append("=" * 60)
        report.append("")
        
        # Weekly stats
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        # Get all alerts from last 7 days
        alerts_file = Path("memory/security/alerts.json")
        if alerts_file.exists():
            with open(alerts_file, 'r') as f:
                all_alerts = json.load(f)
            
            week_alerts = [a for a in all_alerts if a['timestamp'] > week_ago]
            
            report.append("🛡️ SECURITY ALERTS THIS WEEK")
            report.append("-" * 40)
            report.append(f"Total alerts: {len(week_alerts)}")
            
            by_level = {}
            for alert in week_alerts:
                level = alert['level']
                by_level[level] = by_level.get(level, 0) + 1
            
            for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if level in by_level:
                    emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
                    report.append(f"  {emoji.get(level, '⚠️')} {level}: {by_level[level]}")
            report.append("")
        
        # Bouncer stats
        from bouncer import get_bouncer
        bouncer_stats = get_bouncer().get_stats()
        
        report.append("🥊 BOUNCER ENFORCEMENT")
        report.append("-" * 40)
        report.append(f"Total blocked operations: {bouncer_stats['total_blocked']}")
        if bouncer_stats['blocked_by_type']:
            for op_type, count in bouncer_stats['blocked_by_type'].items():
                report.append(f"  - {op_type}: {count}")
        report.append("")
        
        # API spending
        spending_file = Path("memory/api-usage/spending.json")
        if spending_file.exists():
            with open(spending_file, 'r') as f:
                data = json.load(f)
            
            report.append("💰 API SPENDING THIS WEEK")
            report.append("-" * 40)
            report.append(f"Monthly budget: $10.00")
            report.append(f"Total spent: ${data.get('total_spent', 0):.2f}")
            report.append(f"Remaining: ${10.00 - data.get('total_spent', 0):.2f}")
            report.append(f"Total calls: {data.get('total_calls', 0)}")
            report.append("")
        
        # Research findings
        research_dir = Path("outputs/research")
        if research_dir.exists():
            week_files = [f for f in research_dir.glob('*.json') 
                         if f.stat().st_mtime > (datetime.now() - timedelta(days=7)).timestamp()]
            
            report.append("🔍 RESEARCH ACTIVITY")
            report.append("-" * 40)
            report.append(f"Research queries this week: {len(week_files)}")
            report.append("")
        
        report.append("=" * 60)
        report.append("\nCommands:")
        report.append("  python3 tools/cso.py --report       (Full security report)")
        report.append("  python3 tools/bouncer.py --stats    (Bouncer statistics)")
        report.append("  python3 tools/research_agent.py --status  (Spending status)")
        
        return "\n".join(report)
    
    def send_weekly_digest(self, to: str = "jason@allgreatthings.io"):
        """Generate and send weekly digest."""
        report = self.generate_weekly_digest()
        
        # Save to file
        report_file = REPORTS_DIR / f"weekly_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        # Send email
        subject = f"📋 Weekly Security Digest - Week of {datetime.now().strftime('%b %d, %Y')}"
        
        try:
            send_email(to=to, subject=subject, body=report)
            print(f"✓ Weekly digest sent to {to}")
            print(f"  Saved to: {report_file}")
        except Exception as e:
            print(f"✗ Failed to send weekly digest: {e}")


def main():
    parser = argparse.ArgumentParser(description='Scheduled Reports System')
    parser.add_argument('--daily', action='store_true', help='Send daily summary')
    parser.add_argument('--weekly', action='store_true', help='Send weekly digest')
    parser.add_argument('--test-daily', action='store_true', help='Generate daily report (no email)')
    parser.add_argument('--test-weekly', action='store_true', help='Generate weekly report (no email)')
    parser.add_argument('--to', default='jason@allgreatthings.io', help='Email recipient')
    
    args = parser.parse_args()
    
    generator = ReportGenerator()
    
    if args.daily:
        generator.send_daily_report(to=args.to)
    elif args.weekly:
        generator.send_weekly_digest(to=args.to)
    elif args.test_daily:
        print(generator.generate_daily_summary())
    elif args.test_weekly:
        print(generator.generate_weekly_digest())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
