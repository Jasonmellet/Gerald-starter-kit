#!/usr/bin/env python3
"""
Run all scrapers and generate digest.
Main entry point for cron/scheduled runs.
"""

import subprocess
import sys
from pathlib import Path

def run_script(name):
    """Run a scraper script and return success status."""
    script_path = Path(__file__).parent / name
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300
        )
        print(f"\n=== {name} ===")
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {name}: {e}")
        return False

def main():
    print("🚀 Starting Fractional CRO pipeline...")
    print(f"Time: {__import__('datetime').datetime.now()}")
    
    # Ensure DB exists
    run_script('init_db.py')
    
    # Run scrapers
    scrapers = [
        'scrape_upwork.py',
        'scrape_hn.py',
        # 'scrape_linkedin.py',  # Requires Playwright setup
    ]
    
    total_leads = 0
    for scraper in scrapers:
        if run_script(scraper):
            total_leads += 1  # Approximate
    
    # Score leads
    run_script('score_leads.py')
    
    # Generate digest
    run_script('send_digest.py')
    
    print("\n✅ Pipeline complete!")

if __name__ == '__main__':
    main()
