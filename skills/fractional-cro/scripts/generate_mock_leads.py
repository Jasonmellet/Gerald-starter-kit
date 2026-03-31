#!/usr/bin/env python3
"""
Generate mock leads for testing the pipeline.
Useful when live scrapers return no results.
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / 'data' / 'leads.db'

MOCK_LEADS = [
    {
        'source': 'upwork',
        'company': 'TechStart Inc',
        'title': 'Fractional CMO for Series A SaaS',
        'description': 'We just raised our Series A ($8M) and need a fractional CMO to build our marketing function from scratch. Looking for someone who can own GTM strategy, demand gen, and eventually hire a full-time team. Budget: $8-12k/month. Immediate start preferred.',
        'tags': 'series a, saas, immediate'
    },
    {
        'source': 'hackernews',
        'company': 'DataFlow AI',
        'title': 'First Marketing Hire',
        'description': 'YC W24 startup building AI data pipelines. 3 engineers, no marketing. Looking for our first marketing leader — could be fractional to start. Need help with positioning, content, and launching on Product Hunt.',
        'tags': 'yc, ai, first hire'
    },
    {
        'source': 'twitter',
        'company': 'GrowthLabs',
        'title': 'AI Automation Consultant Needed',
        'description': 'Our sales team is drowning in manual work. Looking for someone to build AI agents for lead qualification and follow-up. Budget is flexible for the right person. ASAP.',
        'tags': 'ai agent, sales, automation'
    },
    {
        'source': 'upwork',
        'company': 'HealthTech Co',
        'title': 'Interim Head of Growth',
        'description': 'VP Marketing just left. Need interim support while we search for replacement. 3-6 month engagement. Managing $50k/month ad spend. Healthcare SaaS experience preferred.',
        'tags': 'interim, healthcare, ad spend'
    },
    {
        'source': 'linkedin',
        'company': 'Finova',
        'title': 'Part-Time CMO / Advisor',
        'description': 'Fintech startup seeking experienced marketing leader as advisor. Equity + cash comp. Help us navigate our Series B prep and build the brand. 10-15 hrs/week.',
        'tags': 'fintech, advisor, series b'
    },
    {
        'source': 'twitter',
        'company': 'ShopBuilder',
        'title': 'Need AI Strategy Help',
        'description': 'E-commerce platform with 10k+ merchants. Want to add AI features but don\'t know where to start. Looking for consultant to build AI roadmap and first agent prototypes.',
        'tags': 'ecommerce, ai strategy, roadmap'
    },
    {
        'source': 'hackernews',
        'company': 'DevTools Pro',
        'title': 'Marketing for Developer Tool',
        'description': 'Open source devtool with 50k GitHub stars. Need help monetizing and building enterprise funnel. Technical marketing background required.',
        'tags': 'devtools, open source, enterprise'
    },
    {
        'source': 'upwork',
        'company': 'GreenEnergy Solutions',
        'title': 'Fractional CMO - Clean Tech',
        'description': 'Well-funded cleantech startup ($15M raised) needs marketing leadership. Focus on B2B sales enablement and thought leadership. Competitive salary + equity.',
        'tags': 'cleantech, funded, b2b'
    }
]

def generate_mock_leads():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_new = 0
    
    for i, lead in enumerate(MOCK_LEADS):
        source_id = f"mock_{i}_{datetime.now().strftime('%Y%m%d')}"
        
        # Randomize discovered_at within last 7 days
        days_ago = random.randint(0, 7)
        discovered_at = datetime.now() - timedelta(days=days_ago)
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO leads 
                (source, source_id, company, title, description, tags, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                lead['source'],
                source_id,
                lead['company'],
                lead['title'],
                lead['description'],
                lead['tags'],
                discovered_at
            ))
            
            if cursor.rowcount > 0:
                total_new += 1
                print(f"Added: {lead['company']} - {lead['title']}")
        except Exception as e:
            print(f"Error adding mock lead: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\nTotal mock leads added: {total_new}")
    return total_new

if __name__ == '__main__':
    generate_mock_leads()
