#!/usr/bin/env python3
"""
Conversation & Action Logger
SQLite database for logging all conversations and tool actions.
"""

import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

DB_PATH = Path("memory/gerald_logs.db")


def init_database():
    """Initialize the SQLite database with tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            user_message TEXT,
            assistant_response TEXT,
            channel TEXT DEFAULT 'webchat',
            metadata TEXT
        )
    ''')

    # Actions table (tool calls, API calls, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            action_type TEXT NOT NULL,
            tool_name TEXT,
            input_params TEXT,
            output_result TEXT,
            success BOOLEAN,
            duration_ms INTEGER,
            metadata TEXT
        )
    ''')

    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            channel TEXT,
            user_info TEXT,
            summary TEXT
        )
    ''')

    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_session ON actions(session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type)')

    conn.commit()
    conn.close()
    print(f"✓ Database initialized at {DB_PATH}")


def log_conversation(
    user_message: str,
    assistant_response: str,
    session_id: Optional[str] = None,
    channel: str = 'webchat',
    metadata: Optional[Dict] = None
):
    """Log a conversation exchange."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO conversations (timestamp, session_id, user_message, assistant_response, channel, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        session_id,
        user_message,
        assistant_response,
        channel,
        json.dumps(metadata) if metadata else None
    ))

    conn.commit()
    conn.close()


def log_action(
    action_type: str,
    tool_name: Optional[str] = None,
    input_params: Optional[Dict] = None,
    output_result: Optional[str] = None,
    success: bool = True,
    duration_ms: Optional[int] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """Log a tool action or API call."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO actions (timestamp, session_id, action_type, tool_name, input_params, output_result, success, duration_ms, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        session_id,
        action_type,
        tool_name,
        json.dumps(input_params) if input_params else None,
        output_result,
        success,
        duration_ms,
        json.dumps(metadata) if metadata else None
    ))

    conn.commit()
    conn.close()


def start_session(session_id: str, channel: str = 'webchat', user_info: Optional[Dict] = None):
    """Start a new session."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO sessions (session_id, started_at, channel, user_info)
        VALUES (?, ?, ?, ?)
    ''', (
        session_id,
        datetime.now().isoformat(),
        channel,
        json.dumps(user_info) if user_info else None
    ))

    conn.commit()
    conn.close()


def end_session(session_id: str, summary: Optional[str] = None):
    """End a session."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE sessions SET ended_at = ?, summary = ?
        WHERE session_id = ?
    ''', (
        datetime.now().isoformat(),
        summary,
        session_id
    ))

    conn.commit()
    conn.close()


def get_recent_conversations(limit: int = 10) -> List[Dict]:
    """Get recent conversation entries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM conversations
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_recent_actions(limit: int = 10) -> List[Dict]:
    """Get recent action entries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM actions
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_session_stats(session_id: str) -> Dict:
    """Get stats for a session."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Count conversations
    cursor.execute('SELECT COUNT(*) FROM conversations WHERE session_id = ?', (session_id,))
    conv_count = cursor.fetchone()[0]

    # Count actions
    cursor.execute('SELECT COUNT(*) FROM actions WHERE session_id = ?', (session_id,))
    action_count = cursor.fetchone()[0]

    # Get action breakdown
    cursor.execute('''
        SELECT action_type, COUNT(*) as count
        FROM actions
        WHERE session_id = ?
        GROUP BY action_type
    ''', (session_id,))
    action_breakdown = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return {
        'session_id': session_id,
        'conversation_count': conv_count,
        'action_count': action_count,
        'action_breakdown': action_breakdown
    }


def export_to_json(output_file: str = 'memory/gerald_logs_export.json'):
    """Export all logs to JSON."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Export conversations
    cursor.execute('SELECT * FROM conversations')
    conversations = [dict(row) for row in cursor.fetchall()]

    # Export actions
    cursor.execute('SELECT * FROM actions')
    actions = [dict(row) for row in cursor.fetchall()]

    # Export sessions
    cursor.execute('SELECT * FROM sessions')
    sessions = [dict(row) for row in cursor.fetchall()]

    conn.close()

    export_data = {
        'exported_at': datetime.now().isoformat(),
        'conversations': conversations,
        'actions': actions,
        'sessions': sessions
    }

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"✓ Exported to {output_file}")
    return output_file


def print_stats():
    """Print database statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM conversations')
    conv_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM actions')
    action_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM sessions')
    session_count = cursor.fetchone()[0]

    cursor.execute('''
        SELECT action_type, COUNT(*) as count
        FROM actions
        GROUP BY action_type
        ORDER BY count DESC
    ''')
    action_types = cursor.fetchall()

    conn.close()

    print(f"\n📊 Gerald Log Database Stats")
    print(f"=============================")
    print(f"Database: {DB_PATH}")
    print(f"")
    print(f"Total Conversations: {conv_count}")
    print(f"Total Actions:       {action_count}")
    print(f"Total Sessions:      {session_count}")
    print(f"")
    if action_types:
        print(f"Action Types:")
        for action_type, count in action_types:
            print(f"  - {action_type}: {count}")
    print(f"=============================\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Gerald Logger - Conversation & Action Database')
    parser.add_argument('--init', action='store_true', help='Initialize the database')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--export', action='store_true', help='Export all data to JSON')

    args = parser.parse_args()

    if args.init:
        init_database()
    elif args.stats:
        print_stats()
    elif args.export:
        export_to_json()
    else:
        parser.print_help()
