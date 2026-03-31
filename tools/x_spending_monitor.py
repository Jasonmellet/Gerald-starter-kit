#!/usr/bin/env python3
"""
X API Spending Monitor
Tracks API usage and costs to stay within budget.

Usage:
  python3 tools/x_spending_monitor.py --status
  python3 tools/x_spending_monitor.py --check
  python3 tools/x_spending_monitor.py --alert-limit 5.00
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

SPENDING_FILE = Path(__file__).resolve().parent.parent / "memory" / "x_spending.json"

# X API PAYG pricing (estimated based on current docs)
PRICING = {
    "user_lookup": 0.0025,      # per request
    "tweet_lookup": 0.0025,     # per tweet
    "timeline": 0.0025,         # per tweet returned
    "search": 0.0025,           # per tweet returned
}


def load_spending():
    """Load spending history."""
    if SPENDING_FILE.exists():
        return json.loads(SPENDING_FILE.read_text())
    return {
        "daily": {},
        "total_spent": 0.0,
        "budget_limit": 25.0,  # Your $25 credit
        "alert_threshold": 5.0  # Alert at $5/day
    }


def save_spending(data):
    """Save spending history."""
    SPENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    SPENDING_FILE.write_text(json.dumps(data, indent=2))


def log_request(endpoint_type: str, count: int = 1):
    """Log an API request and its cost."""
    data = load_spending()
    today = datetime.now().strftime("%Y-%m-%d")
    
    cost = PRICING.get(endpoint_type, 0.0025) * count
    
    if today not in data["daily"]:
        data["daily"][today] = {"requests": 0, "cost": 0.0}
    
    data["daily"][today]["requests"] += count
    data["daily"][today]["cost"] += cost
    data["total_spent"] += cost
    
    save_spending(data)
    return cost


def get_status():
    """Get current spending status."""
    data = load_spending()
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    today_stats = data["daily"].get(today, {"requests": 0, "cost": 0.0})
    yesterday_stats = data["daily"].get(yesterday, {"requests": 0, "cost": 0.0})
    
    # Calculate projected monthly cost
    daily_avg = sum(d["cost"] for d in data["daily"].values()) / max(len(data["daily"]), 1)
    projected_monthly = daily_avg * 30
    
    return {
        "today_requests": today_stats["requests"],
        "today_cost": today_stats["cost"],
        "yesterday_cost": yesterday_stats["cost"],
        "total_spent": data["total_spent"],
        "budget_remaining": data["budget_limit"] - data["total_spent"],
        "projected_monthly": projected_monthly,
        "alert_threshold": data["alert_threshold"]
    }


def check_alerts():
    """Check if spending alerts should be triggered."""
    data = load_spending()
    today = datetime.now().strftime("%Y-%m-%d")
    today_cost = data["daily"].get(today, {}).get("cost", 0.0)
    
    alerts = []
    
    if today_cost > data["alert_threshold"]:
        alerts.append(f"⚠️ Daily spending (${today_cost:.2f}) exceeded alert threshold (${data['alert_threshold']:.2f})")
    
    remaining = data["budget_limit"] - data["total_spent"]
    if remaining < 5.0:
        alerts.append(f"🚨 Low budget! Only ${remaining:.2f} remaining of ${data['budget_limit']:.2f}")
    
    return alerts


def print_status():
    """Print spending status."""
    status = get_status()
    
    print("💰 X API Spending Status")
    print("=" * 40)
    print(f"Today:        ${status['today_cost']:.2f} ({status['today_requests']} requests)")
    print(f"Yesterday:    ${status['yesterday_cost']:.2f}")
    print(f"Total spent:  ${status['total_spent']:.2f}")
    print(f"Remaining:    ${status['budget_remaining']:.2f}")
    print(f"Projected:    ${status['projected_monthly']:.2f}/month")
    print(f"Alert at:     ${status['alert_threshold']:.2f}/day")
    print("=" * 40)
    
    if status['today_cost'] > status['alert_threshold']:
        print(f"\n⚠️  ALERT: Daily spending exceeded ${status['alert_threshold']:.2f}!")
    
    if status['budget_remaining'] < 5.0:
        print(f"\n🚨 WARNING: Low budget!")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Monitor X API spending")
    parser.add_argument("--status", action="store_true", help="Show spending status")
    parser.add_argument("--check", action="store_true", help="Check for alerts")
    parser.add_argument("--alert-limit", type=float, help="Set daily alert threshold")
    parser.add_argument("--log", nargs=2, metavar=("TYPE", "COUNT"), help="Log a request")
    
    args = parser.parse_args()
    
    if args.status:
        print_status()
    elif args.check:
        alerts = check_alerts()
        if alerts:
            for alert in alerts:
                print(alert)
            sys.exit(1)
        else:
            print("✓ No spending alerts")
    elif args.alert_limit:
        data = load_spending()
        data["alert_threshold"] = args.alert_limit
        save_spending(data)
        print(f"✓ Alert threshold set to ${args.alert_limit:.2f}/day")
    elif args.log:
        cost = log_request(args.log[0], int(args.log[1]))
        print(f"✓ Logged {args.log[1]} {args.log[0]} request(s): ${cost:.4f}")
    else:
        print_status()


if __name__ == "__main__":
    main()
