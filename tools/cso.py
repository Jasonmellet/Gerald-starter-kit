#!/usr/bin/env python3
"""
Chief Security Officer (CSO) - Autonomous Security Monitoring
Monitors the OpenClaw workspace for threats and suspicious activity.

Codename: Chief
Status: ACTIVE
"""

import os
import sys
import json
import hashlib
import sqlite3
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auto_logger import log_action
from send_email import send_email
from sessions_send import sessions_send

# Paths
SECURITY_DIR = Path("memory/security")
CONFIG_FILE = SECURITY_DIR / "cso-config.json"
ALERTS_FILE = SECURITY_DIR / "alerts.json"
BASELINE_FILE = SECURITY_DIR / "file-baseline.json"
DB_PATH = Path("memory/gerald_logs.db")

# Ensure security directory exists
SECURITY_DIR.mkdir(parents=True, exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    "alert_email": "jason@allgreatthings.io",
    "monitor_interval_minutes": 15,
    "allowed_directories": ["/Users/jcore/Desktop/Openclaw"],
    "blocked_domains": [],
    "whitelisted_skills": [],
    "blacklisted_skills": [],
    "auto_block_high_risk": True,
    "max_daily_api_spend": 10.00,
    "suspicious_patterns": [
        "eval(",
        "exec(",
        "__import__('os').system",
        "base64.b64decode",
        "subprocess.call",
        "os.system("
    ],
    "sensitive_files": [
        ".env",
        "credentials/",
        "memory/gerald_logs.db"
    ]
}


class ChiefSecurityOfficer:
    """Chief Security Officer - monitors and protects the workspace."""
    
    def __init__(self):
        self.config = self._load_config()
        self.alerts = []
        
    def _load_config(self) -> Dict:
        """Load or create CSO configuration."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        
        # Create default config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    
    def _save_alert(self, level: str, category: str, message: str, details: Dict = None):
        """Save a security alert."""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "category": category,
            "message": message,
            "details": details or {}
        }
        
        # Load existing alerts
        alerts = []
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)
        
        alerts.append(alert)
        
        # Keep only last 1000 alerts
        alerts = alerts[-1000:]
        
        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
        
        # Log to database
        log_action(
            action_type='security_alert',
            tool_name='CSO',
            input_params={'level': level, 'category': category},
            output_result=message,
            success=(level != 'CRITICAL'),
            metadata={'alert': alert}
        )
        
        # Send email for HIGH and CRITICAL
        if level in ['HIGH', 'CRITICAL']:
            self._send_alert_email(alert)
        
        # Send Telegram alerts for all levels (staff notifications)
        self._send_alert_telegram(alert)
        
        return alert
    
    def _send_alert_email(self, alert: Dict):
        """Send email alert for high/critical issues."""
        try:
            emoji = {"HIGH": "🟠", "CRITICAL": "🔴"}.get(alert['level'], "⚠️")
            subject = f"{emoji} SECURITY ALERT: {alert['category']} - {alert['level']}"
            
            body = f"""Chief Security Officer Alert

Level: {alert['level']}
Category: {alert['category']}
Time: {alert['timestamp']}

{alert['message']}

Details:
{json.dumps(alert.get('details', {}), indent=2)}

---
This is an automated security alert from Chief.
View all alerts: python3 tools/cso.py --alerts
"""
            
            send_email(
                to=self.config['alert_email'],
                subject=subject,
                body=body
            )
        except Exception as e:
            print(f"Failed to send alert email: {e}")
    
    def _send_alert_telegram(self, alert: Dict):
        """Send alert to Telegram for staff notifications."""
        if not self.config.get('alert_telegram', False):
            return
        
        try:
            emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
            level_emoji = emoji.get(alert['level'], "⚠️")
            
            message = f"""🛡️ <b>Chief Security Alert</b>

{level_emoji} <b>Level:</b> {alert['level']}
📁 <b>Category:</b> {alert['category']}
🕐 <b>Time:</b> {alert['timestamp']}

{alert['message']}

<i>Alert from Chief Security Officer</i>"""
            
            chat_id = self.config.get('telegram_chat_id', '8130598479')
            sessions_send(chat_id, message)
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")
    
    def check_file_integrity(self) -> List[Dict]:
        """Check file integrity against baseline."""
        alerts = []
        
        # Generate current file hashes for sensitive files
        current_hashes = {}
        for pattern in self.config['sensitive_files']:
            if pattern.endswith('/'):
                # Directory
                for f in Path('.').glob(f"{pattern}**/*"):
                    if f.is_file():
                        current_hashes[str(f)] = self._hash_file(f)
            else:
                # Single file
                f = Path(pattern)
                if f.exists():
                    current_hashes[str(f)] = self._hash_file(f)
        
        # Load baseline
        baseline = {}
        if BASELINE_FILE.exists():
            with open(BASELINE_FILE, 'r') as f:
                baseline = json.load(f)
        else:
            # First run - create baseline
            with open(BASELINE_FILE, 'w') as f:
                json.dump(current_hashes, f, indent=2)
            print("✓ Created file integrity baseline")
            return []
        
        # Compare
        for filepath, current_hash in current_hashes.items():
            if filepath in baseline:
                if baseline[filepath] != current_hash:
                    alert = self._save_alert(
                        'MEDIUM',
                        'file_integrity',
                        f'File modified: {filepath}',
                        {'file': filepath}
                    )
                    alerts.append(alert)
            else:
                # New file
                alert = self._save_alert(
                    'LOW',
                    'file_creation',
                    f'New file detected: {filepath}',
                    {'file': filepath}
                )
                alerts.append(alert)
        
        # Check for deleted files
        for filepath in baseline:
            if filepath not in current_hashes:
                alert = self._save_alert(
                    'MEDIUM',
                    'file_deletion',
                    f'File deleted: {filepath}',
                    {'file': filepath}
                )
                alerts.append(alert)
        
        # Update baseline
        with open(BASELINE_FILE, 'w') as f:
            json.dump(current_hashes, f, indent=2)
        
        return alerts
    
    def _hash_file(self, filepath: Path) -> str:
        """Generate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def scan_skills(self) -> List[Dict]:
        """Scan installed skills for suspicious patterns."""
        alerts = []
        skills_dir = Path('skills')
        
        if not skills_dir.exists():
            return alerts
        
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_name = skill_dir.name
            
            # Check if blacklisted
            if skill_name in self.config.get('blacklisted_skills', []):
                alert = self._save_alert(
                    'HIGH',
                    'blacklisted_skill',
                    f'Blacklisted skill detected: {skill_name}',
                    {'skill': skill_name}
                )
                alerts.append(alert)
                continue
            
            # Scan Python files for suspicious patterns
            for py_file in skill_dir.rglob('*.py'):
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                    
                    for pattern in self.config['suspicious_patterns']:
                        if pattern in content:
                            alert = self._save_alert(
                                'MEDIUM',
                                'suspicious_code',
                                f'Suspicious pattern found in {py_file}',
                                {
                                    'skill': skill_name,
                                    'file': str(py_file),
                                    'pattern': pattern
                                }
                            )
                            alerts.append(alert)
                except Exception as e:
                    pass
        
        return alerts
    
    def check_api_spending(self) -> List[Dict]:
        """Check for unusual API spending."""
        alerts = []
        
        # Load spending data
        spending_file = Path('memory/api-usage/spending.json')
        if not spending_file.exists():
            return alerts
        
        with open(spending_file, 'r') as f:
            data = json.load(f)
        
        today = datetime.now().strftime('%Y-%m-%d')
        day_data = data.get('by_day', {}).get(today, {'spent': 0.0, 'calls': 0})
        
        daily_spent = day_data.get('spent', 0.0)
        daily_calls = day_data.get('calls', 0)
        
        # Alert on high daily spend
        if daily_spent > 5.00:  # Half the monthly budget in one day
            alert = self._save_alert(
                'HIGH',
                'api_spending',
                f'Unusual API spending: ${daily_spent:.2f} today',
                {'daily_spent': daily_spent, 'calls': daily_calls}
            )
            alerts.append(alert)
        elif daily_spent > 2.00:
            alert = self._save_alert(
                'MEDIUM',
                'api_spending',
                f'Elevated API spending: ${daily_spent:.2f} today',
                {'daily_spent': daily_spent, 'calls': daily_calls}
            )
            alerts.append(alert)
        
        return alerts
    
    def check_recent_activity(self, hours: int = 24) -> Dict:
        """Check recent database activity for anomalies."""
        if not DB_PATH.exists():
            return {'error': 'Database not found'}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Count recent actions
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT action_type, COUNT(*) as count
            FROM actions
            WHERE timestamp > ?
            GROUP BY action_type
        ''', (since,))
        
        actions = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count recent alerts
        cursor.execute('''
            SELECT COUNT(*) FROM actions
            WHERE action_type = 'security_alert' AND timestamp > ?
        ''', (since,))
        
        alert_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'period_hours': hours,
            'actions': actions,
            'security_alerts': alert_count
        }
    
    def generate_report(self) -> str:
        """Generate comprehensive security report."""
        report = []
        report.append("=" * 60)
        report.append("CHIEF SECURITY OFFICER REPORT")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("=" * 60)
        report.append("")
        
        # Recent activity
        activity = self.check_recent_activity(24)
        report.append("📊 RECENT ACTIVITY (Last 24h)")
        report.append("-" * 40)
        for action_type, count in activity.get('actions', {}).items():
            report.append(f"  {action_type}: {count}")
        report.append(f"  Security alerts: {activity.get('security_alerts', 0)}")
        report.append("")
        
        # File integrity
        report.append("🔒 FILE INTEGRITY")
        report.append("-" * 40)
        if BASELINE_FILE.exists():
            with open(BASELINE_FILE, 'r') as f:
                baseline = json.load(f)
            report.append(f"  Files monitored: {len(baseline)}")
        report.append("")
        
        # API spending
        spending_file = Path('memory/api-usage/spending.json')
        if spending_file.exists():
            with open(spending_file, 'r') as f:
                data = json.load(f)
            report.append("💰 API SPENDING")
            report.append("-" * 40)
            report.append(f"  Monthly budget: ${self.config['max_daily_api_spend'] * 30:.2f}")
            report.append(f"  Spent this month: ${data.get('total_spent', 0):.2f}")
            report.append("")
        
        # Recent alerts
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)
            
            # Get last 24h alerts
            since = (datetime.now() - timedelta(hours=24)).isoformat()
            recent_alerts = [a for a in alerts if a['timestamp'] > since]
            
            if recent_alerts:
                report.append("⚠️ RECENT ALERTS (Last 24h)")
                report.append("-" * 40)
                for alert in recent_alerts[-5:]:  # Last 5
                    emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
                    report.append(f"  {emoji.get(alert['level'], '⚠️')} [{alert['level']}] {alert['category']}")
                    report.append(f"      {alert['message'][:60]}...")
                report.append("")
        
        # Config status
        report.append("⚙️ SECURITY CONFIGURATION")
        report.append("-" * 40)
        report.append(f"  Auto-block high risk: {self.config.get('auto_block_high_risk', False)}")
        report.append(f"  Blacklisted skills: {len(self.config.get('blacklisted_skills', []))}")
        report.append(f"  Suspicious patterns: {len(self.config.get('suspicious_patterns', []))}")
        report.append("")
        
        report.append("=" * 60)
        report.append("Chief is watching. Stay safe.")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def run_full_scan(self) -> List[Dict]:
        """Run a complete security scan."""
        print("🔍 Chief Security Officer - Running full scan...")
        print()
        
        all_alerts = []
        
        # File integrity
        print("Checking file integrity...")
        alerts = self.check_file_integrity()
        all_alerts.extend(alerts)
        print(f"  ✓ {len(alerts)} file integrity alerts")
        
        # Skill scan
        print("Scanning skills...")
        alerts = self.scan_skills()
        all_alerts.extend(alerts)
        print(f"  ✓ {len(alerts)} skill alerts")
        
        # API spending
        print("Checking API spending...")
        alerts = self.check_api_spending()
        all_alerts.extend(alerts)
        print(f"  ✓ {len(alerts)} spending alerts")
        
        print()
        print(f"Scan complete. {len(all_alerts)} alerts generated.")
        
        return all_alerts


def main():
    parser = argparse.ArgumentParser(
        description='Chief Security Officer - Autonomous Security Monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check security status
  python3 tools/cso.py --status

  # Run full security scan
  python3 tools/cso.py --scan

  # View recent alerts
  python3 tools/cso.py --alerts --last 24h

  # Generate security report
  python3 tools/cso.py --report

  # Start continuous monitoring
  python3 tools/cso.py --monitor
        """
    )
    
    parser.add_argument('--status', action='store_true', help='Check current security status')
    parser.add_argument('--scan', action='store_true', help='Run full security scan')
    parser.add_argument('--alerts', action='store_true', help='Show recent alerts')
    parser.add_argument('--last', type=int, default=24, help='Hours of history (default: 24)')
    parser.add_argument('--integrity-check', action='store_true', help='Check file integrity')
    parser.add_argument('--report', action='store_true', help='Generate security report')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    
    args = parser.parse_args()
    
    chief = ChiefSecurityOfficer()
    
    if args.scan:
        chief.run_full_scan()
    
    elif args.integrity_check:
        alerts = chief.check_file_integrity()
        print(f"File integrity check: {len(alerts)} alerts")
        for alert in alerts:
            print(f"  [{alert['level']}] {alert['message']}")
    
    elif args.alerts:
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)
            
            since = (datetime.now() - timedelta(hours=args.last)).isoformat()
            recent = [a for a in alerts if a['timestamp'] > since]
            
            print(f"\nAlerts from last {args.last} hours: {len(recent)}")
            for alert in recent:
                emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
                print(f"\n{emoji.get(alert['level'], '⚠️')} [{alert['level']}] {alert['category']}")
                print(f"   {alert['timestamp']}")
                print(f"   {alert['message']}")
        else:
            print("No alerts file found.")
    
    elif args.report:
        report = chief.generate_report()
        print(report)
        
        # Save report
        report_file = SECURITY_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n✓ Report saved to: {report_file}")
    
    elif args.monitor:
        print("🛡️  Chief Security Officer - Starting continuous monitoring...")
        print(f"   Monitoring interval: {chief.config['monitor_interval_minutes']} minutes")
        print(f"   Alerts go to: {chief.config['alert_email']}")
        print("   Press Ctrl+C to stop\n")
        
        import time
        try:
            while True:
                chief.run_full_scan()
                print(f"\n💤 Sleeping for {chief.config['monitor_interval_minutes']} minutes...")
                time.sleep(chief.config['monitor_interval_minutes'] * 60)
        except KeyboardInterrupt:
            print("\n\n👋 Chief signing off. Stay safe.")
    
    elif args.status:
        activity = chief.check_recent_activity(24)
        print("\n🛡️  Chief Security Officer Status")
        print("=" * 50)
        print(f"Configuration: {CONFIG_FILE.exists()}")
        print(f"Alerts file: {ALERTS_FILE.exists()}")
        print(f"Baseline: {BASELINE_FILE.exists()}")
        print(f"\nLast 24h activity:")
        for action_type, count in activity.get('actions', {}).items():
            print(f"  {action_type}: {count}")
        print(f"\nSecurity alerts: {activity.get('security_alerts', 0)}")
        print("=" * 50)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
