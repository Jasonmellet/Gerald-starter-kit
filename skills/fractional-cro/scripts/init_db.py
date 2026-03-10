#!/usr/bin/env python3
"""
Initialize SQLite database for lead tracking.
Run once to set up the database schema.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'leads.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT UNIQUE,
            company TEXT,
            contact_name TEXT,
            title TEXT,
            url TEXT,
            description TEXT,
            budget_signals TEXT,
            urgency_signals TEXT,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new',
            tags TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            contacted_at TIMESTAMP,
            notes TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            type TEXT,
            content TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            response_received BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            cost_usd REAL,
            usage_count INTEGER,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == '__main__':
    init_db()
