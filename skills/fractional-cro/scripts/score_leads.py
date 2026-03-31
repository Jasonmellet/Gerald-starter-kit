#!/usr/bin/env python3
"""
Score leads based on budget signals, urgency, and fit.
Updates the database with calculated scores.
"""

import sqlite3
import json
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'leads.db'
CONFIG_PATH = Path(__file__).parent.parent / 'config.json'

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {
        'scoring': {
            'budget_weight': 0.4,
            'urgency_weight': 0.3,
            'fit_weight': 0.3
        }
    }

def calculate_budget_score(description: str) -> int:
    """Score based on budget signals in description."""
    score = 50  # baseline
    
    # High budget signals
    high_signals = [
        r'\$\d{2,3},?\d{3}',  # $50k, $100k
        r'funded', 'series a', 'series b', 'venture backed',
        'well funded', 'generous budget', 'competitive salary',
        'enterprise', 'fortune 500'
    ]
    
    # Medium budget signals
    medium_signals = [
        r'\$\d{1,2},?\d{3}/month',
        'startup', 'growing fast', 'scaling',
        'multiple clients', 'ongoing work'
    ]
    
    desc_lower = description.lower()
    
    for signal in high_signals:
        if re.search(signal, desc_lower, re.IGNORECASE):
            score += 25
            break
    
    for signal in medium_signals:
        if re.search(signal, desc_lower, re.IGNORECASE):
            score += 15
            break
    
    return min(score, 100)

def calculate_urgency_score(description: str) -> int:
    """Score based on urgency signals."""
    score = 50
    
    urgent_signals = [
        'asap', 'immediately', 'urgent', 'this week',
        'start monday', 'need help now', 'critical',
        'falling behind', 'overwhelmed'
    ]
    
    desc_lower = description.lower()
    
    for signal in urgent_signals:
        if signal in desc_lower:
            score += 30
            break
    
    return min(score, 100)

def calculate_fit_score(description: str) -> int:
    """Score based on fit for fractional CMO / AI agent work."""
    score = 50
    
    perfect_fit = [
        'fractional cmo', 'part-time cmo', 'interim cmo',
        'first marketing hire', 'marketing leader',
        'ai agent', 'automation', 'llm', 'ai strategy'
    ]
    
    good_fit = [
        'growth marketing', 'demand gen', 'go-to-market',
        'marketing strategy', 'digital transformation',
        'process automation', 'efficiency'
    ]
    
    desc_lower = description.lower()
    
    for signal in perfect_fit:
        if signal in desc_lower:
            score += 40
            break
    else:
        for signal in good_fit:
            if signal in desc_lower:
                score += 20
                break
    
    return min(score, 100)

def score_leads():
    config = load_config()
    weights = config['scoring']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, description FROM leads WHERE score = 0 OR score IS NULL")
    leads = cursor.fetchall()
    
    for lead_id, description in leads:
        budget = calculate_budget_score(description or '')
        urgency = calculate_urgency_score(description or '')
        fit = calculate_fit_score(description or '')
        
        total_score = int(
            budget * weights['budget_weight'] +
            urgency * weights['urgency_weight'] +
            fit * weights['fit_weight']
        )
        
        cursor.execute(
            "UPDATE leads SET score = ?, budget_signals = ?, urgency_signals = ? WHERE id = ?",
            (total_score, str(budget), str(urgency), lead_id)
        )
    
    conn.commit()
    conn.close()
    print(f"Scored {len(leads)} leads")

if __name__ == '__main__':
    score_leads()
