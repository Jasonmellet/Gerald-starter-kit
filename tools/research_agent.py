#!/usr/bin/env python3
"""
Research Agent for Self-Improvement
Uses DataForSEO API with spending limits and full audit logging.

Budget: $10/month (~500 calls)
Safety: Hard limits, daily caps, full audit trail
"""

import os
import sys

# Load .env from repo root
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
import base64
import requests
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional

# Budget configuration
MONTHLY_BUDGET = 10.00  # Dollars
DAILY_CALL_LIMIT = 20
MAX_COST_PER_QUERY = 0.50  # Dollars
ESTIMATED_COST_PER_CALL = 0.02  # Dollars

# API endpoints
DATAFORSEO_BASE = "https://api.dataforseo.com/v3"


class SpendingTracker:
    """Track API spending with daily/weekly/monthly limits."""

    def __init__(self, base_dir: str = "memory/api-usage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.spending_file = self.base_dir / "spending.json"
        self.today = date.today().isoformat()
        self.this_month = date.today().strftime("%Y-%m")

    def _load_spending(self) -> Dict[str, Any]:
        """Load current spending data."""
        if self.spending_file.exists():
            with open(self.spending_file, 'r') as f:
                return json.load(f)
        return {
            "monthly_budget": MONTHLY_BUDGET,
            "total_spent": 0.0,
            "total_calls": 0,
            "by_month": {},
            "by_day": {}
        }

    def _save_spending(self, data: Dict[str, Any]):
        """Save spending data."""
        with open(self.spending_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_current_usage(self) -> Dict[str, Any]:
        """Get current month and day usage."""
        data = self._load_spending()
        month_data = data.get("by_month", {}).get(self.this_month, {"spent": 0.0, "calls": 0})
        day_data = data.get("by_day", {}).get(self.today, {"spent": 0.0, "calls": 0})
        return {
            "monthly_spent": month_data.get("spent", 0.0),
            "monthly_calls": month_data.get("calls", 0),
            "daily_calls": day_data.get("calls", 0),
            "budget_remaining": MONTHLY_BUDGET - month_data.get("spent", 0.0),
            "calls_remaining_today": DAILY_CALL_LIMIT - day_data.get("calls", 0)
        }

    def can_make_call(self, estimated_cost: float = ESTIMATED_COST_PER_CALL) -> tuple[bool, str]:
        """Check if a new API call is allowed."""
        usage = self.get_current_usage()

        # Check monthly budget
        if usage["monthly_spent"] + estimated_cost > MONTHLY_BUDGET:
            return False, f"Monthly budget exceeded: ${usage['monthly_spent']:.2f} / ${MONTHLY_BUDGET:.2f}"

        # Check daily call limit
        if usage["daily_calls"] >= DAILY_CALL_LIMIT:
            return False, f"Daily call limit reached: {usage['daily_calls']} / {DAILY_CALL_LIMIT}"

        # Check per-query cost
        if estimated_cost > MAX_COST_PER_QUERY:
            return False, f"Query too expensive: ${estimated_cost:.2f} > ${MAX_COST_PER_QUERY:.2f} max"

        return True, "OK"

    def log_call(self, query: str, endpoint: str, cost: float, results_count: int, notes: str = ""):
        """Log an API call to daily file and update totals."""
        # Update daily log
        daily_file = self.base_dir / f"{self.today}.json"
        daily_log = []
        if daily_file.exists():
            with open(daily_file, 'r') as f:
                daily_log = json.load(f)

        call_record = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "endpoint": endpoint,
            "cost": cost,
            "results_count": results_count,
            "notes": notes
        }
        daily_log.append(call_record)

        with open(daily_file, 'w') as f:
            json.dump(daily_log, f, indent=2)

        # Update spending totals
        data = self._load_spending()

        # Update month
        if self.this_month not in data["by_month"]:
            data["by_month"][self.this_month] = {"spent": 0.0, "calls": 0}
        data["by_month"][self.this_month]["spent"] += cost
        data["by_month"][self.this_month]["calls"] += 1

        # Update day
        if self.today not in data["by_day"]:
            data["by_day"][self.today] = {"spent": 0.0, "calls": 0}
        data["by_day"][self.today]["spent"] += cost
        data["by_day"][self.today]["calls"] += 1

        # Update totals
        data["total_spent"] += cost
        data["total_calls"] += 1

        self._save_spending(data)

    def print_status(self):
        """Print current spending status."""
        usage = self.get_current_usage()
        print(f"\n📊 Research Agent Spending Status")
        print(f"=================================")
        print(f"Monthly Budget:     ${MONTHLY_BUDGET:.2f}")
        print(f"Monthly Spent:      ${usage['monthly_spent']:.2f}")
        print(f"Budget Remaining:   ${usage['budget_remaining']:.2f}")
        print(f"")
        print(f"Monthly Calls:      {usage['monthly_calls']}")
        print(f"Today's Calls:      {usage['daily_calls']} / {DAILY_CALL_LIMIT}")
        print(f"Calls Left Today:   {usage['calls_remaining_today']}")
        print(f"")
        print(f"Cost per call:      ~${ESTIMATED_COST_PER_CALL:.2f}")
        print(f"Max per query:      ${MAX_COST_PER_QUERY:.2f}")
        print(f"=================================\n")


class DataForSEOClient:
    """Client for DataForSEO API with spending tracking."""

    def __init__(self):
        self.login = os.getenv("DATAFORSEO_LOGIN", "").strip()
        self.password = os.getenv("DATAFORSEO_PASSWORD", "").strip()
        self.location_code = int(os.getenv("DATAFORSEO_LOCATION_CODE", "2840"))
        self.language_code = os.getenv("DATAFORSEO_LANGUAGE_CODE", "en")
        self.tracker = SpendingTracker()

        if not self.login or not self.password:
            raise ValueError("DataForSEO credentials not found in environment")

        # Create auth header
        credentials = base64.b64encode(f"{self.login}:{self.password}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json"
        }

    def search_serp(self, query: str, num_results: int = 10) -> Optional[Dict[str, Any]]:
        """
        Perform a SERP search.

        Args:
            query: Search query
            num_results: Number of results (max 100)

        Returns:
            Search results or None if budget exceeded
        """
        # Check budget
        can_call, reason = self.tracker.can_make_call()
        if not can_call:
            print(f"❌ Budget check failed: {reason}")
            return None

        endpoint = f"{DATAFORSEO_BASE}/serp/google/organic/live/advanced"

        payload = [{
            "keyword": query,
            "location_code": self.location_code,
            "language_code": self.language_code,
            "depth": min(num_results, 100),
            "device": "desktop"
        }]

        try:
            print(f"🔍 Searching: '{query}'")
            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract results
            results = self._extract_serp_results(data)

            # Log the call
            self.tracker.log_call(
                query=query,
                endpoint="serp/google/organic/live/advanced",
                cost=ESTIMATED_COST_PER_CALL,
                results_count=len(results),
                notes=f"SERP search for '{query}'"
            )

            print(f"✓ Found {len(results)} results")
            return {
                "query": query,
                "results": results,
                "raw_response": data
            }

        except requests.exceptions.RequestException as e:
            print(f"❌ API error: {e}")
            return None

    def _extract_serp_results(self, data: Dict) -> List[Dict]:
        """Extract clean results from SERP response."""
        results = []

        tasks = data.get("tasks", [])
        for task in tasks:
            for result in task.get("result", []):
                items = result.get("items", [])
                for item in items:
                    if item.get("type") == "organic":
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": item.get("description", ""),
                            "position": item.get("rank_absolute", 0)
                        })

        return results

    def get_trends(self, keywords: List[str]) -> Optional[Dict[str, Any]]:
        """
        Get search trends for keywords.

        Args:
            keywords: List of keywords to check

        Returns:
            Trends data or None if budget exceeded
        """
        # Check budget
        can_call, reason = self.tracker.can_make_call()
        if not can_call:
            print(f"❌ Budget check failed: {reason}")
            return None

        endpoint = f"{DATAFORSEO_BASE}/keywords_data/google/search_volume/live"

        payload = []
        for keyword in keywords:
            payload.append({
                "keyword": keyword,
                "location_code": self.location_code,
                "language_code": self.language_code
            })

        try:
            print(f"📈 Checking trends for: {', '.join(keywords)}")
            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract trend data
            trends = self._extract_trends(data)

            # Log the call
            self.tracker.log_call(
                query=f"trends: {', '.join(keywords)}",
                endpoint="keywords_data/google/search_volume/live",
                cost=ESTIMATED_COST_PER_CALL,
                results_count=len(trends),
                notes=f"Trend data for {len(keywords)} keywords"
            )

            print(f"✓ Retrieved trends for {len(trends)} keywords")
            return {
                "keywords": keywords,
                "trends": trends,
                "raw_response": data
            }

        except requests.exceptions.RequestException as e:
            print(f"❌ API error: {e}")
            return None

    def _extract_trends(self, data: Dict) -> List[Dict]:
        """Extract trend data from response."""
        trends = []

        tasks = data.get("tasks", [])
        for task in tasks:
            for result in task.get("result", []):
                keyword = result.get("keyword", "")
                monthly_searches = result.get("monthly_searches", [])
                search_volume = result.get("search_volume", 0)

                trends.append({
                    "keyword": keyword,
                    "search_volume": search_volume,
                    "monthly_data": monthly_searches
                })

        return trends


def research_topic(query: str, num_results: int = 10):
    """Research a topic and return formatted results."""
    client = DataForSEOClient()

    # Print budget status first
    client.tracker.print_status()

    # Perform search
    result = client.search_serp(query, num_results)

    if not result:
        print("❌ No results (budget exceeded or API error)")
        return

    # Format output
    print(f"\n📝 Research Results: {query}")
    print(f"{'=' * 60}")

    for item in result["results"]:
        print(f"\n{item['position']}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   {item['description'][:150]}...")

    # Save to outputs
    output_dir = Path("outputs/research")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c if c.isalnum() else "_" for c in query[:50])
    output_file = output_dir / f"{timestamp}_{safe_query}.json"

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")


def check_trends(keywords: List[str]):
    """Check search trends for keywords."""
    client = DataForSEOClient()

    # Print budget status
    client.tracker.print_status()

    # Get trends
    result = client.get_trends(keywords)

    if not result:
        print("❌ No trend data (budget exceeded or API error)")
        return

    # Format output
    print(f"\n📊 Trend Analysis")
    print(f"{'=' * 60}")

    for trend in result["trends"]:
        print(f"\n🔍 {trend['keyword']}")
        print(f"   Monthly searches: {trend['search_volume']:,}")
        if trend['monthly_data']:
            recent = trend['monthly_data'][-3:]  # Last 3 months
            print(f"   Recent trend: ", end="")
            for month in recent:
                print(f"{month['month']}/{month['year']}: {month['search_volume']:,}  ", end="")
            print()


def print_audit_log(days: int = 7):
    """Print recent audit log."""
    tracker = SpendingTracker()
    base_dir = Path("memory/api-usage")

    print(f"\n📋 Recent API Activity (last {days} days)")
    print(f"{'=' * 60}")

    total_calls = 0
    total_cost = 0.0

    for i in range(days):
        check_date = (date.today() - __import__('datetime').timedelta(days=i)).isoformat()
        daily_file = base_dir / f"{check_date}.json"

        if daily_file.exists():
            with open(daily_file, 'r') as f:
                calls = json.load(f)

            day_cost = sum(c.get("cost", 0) for c in calls)
            total_calls += len(calls)
            total_cost += day_cost

            print(f"\n{check_date}: {len(calls)} calls, ${day_cost:.2f}")
            for call in calls[-3:]:  # Show last 3
                print(f"  - {call['timestamp'][11:19]}: '{call['query'][:40]}...' (${call['cost']:.2f})")

    print(f"\n{'=' * 60}")
    print(f"Total: {total_calls} calls, ${total_cost:.2f}")


def main():
    parser = argparse.ArgumentParser(
        description='Research Agent - Self-improvement via DataForSEO',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Research a topic
  python3 tools/research_agent.py --query "OpenClaw AI agent improvements"

  # Check trends
  python3 tools/research_agent.py --trends --keywords "AI agents,OpenClaw,automation"

  # Check budget status
  python3 tools/research_agent.py --status

  # View audit log
  python3 tools/research_agent.py --audit
        """
    )

    parser.add_argument('--query', '-q', help='Research query to search')
    parser.add_argument('--results', '-r', type=int, default=10, help='Number of results (default: 10)')
    parser.add_argument('--trends', action='store_true', help='Check trends mode')
    parser.add_argument('--keywords', '-k', help='Comma-separated keywords for trends')
    parser.add_argument('--status', action='store_true', help='Show spending status')
    parser.add_argument('--audit', action='store_true', help='Show recent audit log')
    parser.add_argument('--days', type=int, default=7, help='Days of audit history (default: 7)')

    args = parser.parse_args()

    try:
        if args.status:
            tracker = SpendingTracker()
            tracker.print_status()

        elif args.audit:
            print_audit_log(args.days)

        elif args.trends:
            if not args.keywords:
                # Default keywords for self-improvement
                args.keywords = "AI agents,OpenClaw,marketing automation,LLM improvements"
            keywords = [k.strip() for k in args.keywords.split(',')]
            check_trends(keywords)

        elif args.query:
            research_topic(args.query, args.results)

        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
