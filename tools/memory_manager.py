#!/usr/bin/env python3
"""
Memory Manager - Smart Context Retrieval and Learning
Makes Gerald actually USE his memory instead of just storing it.
"""

import os
import sys
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent))

# Paths
MEMORY_DIR = Path("memory")
AGENT_LAB = Path("agent-lab")
DB_PATH = MEMORY_DIR / "gerald_logs.db"
MEMORY_MD = AGENT_LAB / "MEMORY.md"

@dataclass
class ConversationSummary:
    """Summary of a conversation."""
    timestamp: str
    topic: str
    key_points: List[str]
    decisions_made: List[str]
    tools_created: List[str]
    user_preferences_expressed: List[str]


class MemoryManager:
    """Manages Gerald's memory and context retrieval."""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.memory_dir = MEMORY_DIR
        self.memory_dir.mkdir(exist_ok=True)
        
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def search_conversations(self, query: str, limit: int = 5) -> List[Dict]:
        """Search past conversations for relevant context."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Simple keyword search (could be enhanced with embeddings)
        keywords = query.lower().split()
        
        cursor.execute('''
            SELECT * FROM conversations
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        
        all_convos = cursor.fetchall()
        conn.close()
        
        # Score by keyword match
        scored = []
        for convo in all_convos:
            text = f"{convo['user_message']} {convo['assistant_response']}".lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, convo))
        
        # Sort by score and return top matches
        scored.sort(key=lambda x: x[0], reverse=True)
        return [dict(row) for _, row in scored[:limit]]
    
    def get_recent_context(self, hours: int = 24) -> str:
        """Get context from recent activity."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # Get recent conversations
        cursor.execute('''
            SELECT * FROM conversations
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (since,))
        
        recent_convos = cursor.fetchall()
        
        # Get recent actions
        cursor.execute('''
            SELECT * FROM actions
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (since,))
        
        recent_actions = cursor.fetchall()
        
        conn.close()
        
        # Build context string
        context = []
        context.append(f"Recent Activity (last {hours}h):\n")
        
        if recent_convos:
            context.append("Key Conversations:")
            for convo in recent_convos[:3]:
                context.append(f"- {convo['timestamp'][:16]}: {convo['user_message'][:80]}...")
        
        if recent_actions:
            context.append("\nKey Actions:")
            for action in recent_actions[:5]:
                tool_name = action['tool_name'] if 'tool_name' in action.keys() else 'N/A'
                context.append(f"- {action['action_type']}: {tool_name}")
        
        return "\n".join(context)
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Extract user preferences from conversations."""
        # Load from USER.md if it exists
        user_md = AGENT_LAB / "USER.md"
        preferences = {
            "communication_style": "direct",  # Based on "no fluff" comment
            "humor": "appreciated",
            "interests": ["marketing automation", "efficiency", "optimization"],
            "work": "marketing and sales automation (cold email, PPC, SEO, ABM, CRO)",
            "personal": "married, 2 kids, dog, likes wine and steaks"
        }
        
        if user_md.exists():
            with open(user_md, 'r') as f:
                content = f.read()
                # Parse key info
                if "no fluff" in content.lower():
                    preferences["communication_style"] = "direct, no fluff"
                if "humor" in content.lower():
                    preferences["humor"] = "appreciated"
        
        return preferences
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get summary of a specific session."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sessions WHERE session_id = ?
        ''', (session_id,))
        
        session = cursor.fetchone()
        conn.close()
        
        if session:
            return dict(session)
        return None
    
    def summarize_current_session(self) -> ConversationSummary:
        """Auto-summarize the current session's activity."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Get today's conversations
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT * FROM conversations
            WHERE timestamp LIKE ?
            ORDER BY timestamp ASC
        ''', (f'{today}%',))
        
        convos = cursor.fetchall()
        
        # Get today's actions
        cursor.execute('''
            SELECT * FROM actions
            WHERE timestamp LIKE ?
            ORDER BY timestamp ASC
        ''', (f'{today}%',))
        
        actions = cursor.fetchall()
        
        conn.close()
        
        if not convos:
            return ConversationSummary(
                timestamp=today,
                topic="No activity",
                key_points=[],
                decisions_made=[],
                tools_created=[],
                user_preferences_expressed=[]
            )
        
        # Extract key info
        all_text = " ".join([c['user_message'] + " " + c['assistant_response'] for c in convos])
        
        # Simple extraction (could use LLM for better summarization)
        key_points = []
        tools_created = []
        decisions = []
        
        for action in actions:
            action_type = action['action_type']
            tool_name = action['tool_name'] if 'tool_name' in action.keys() else ''
            
            if action_type == 'file_operation' and 'write' in str(action['input_params'] if 'input_params' in action.keys() else '{}'):
                params = action['input_params'] if 'input_params' in action.keys() else '{}'
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except:
                        params = {}
                filepath = params.get('file', '')
                if filepath and '.' in filepath:
                    tools_created.append(filepath)
            
            if action_type in ['cso_initialized', 'security_threat_intel']:
                key_points.append(f"Security: {action['output_result'][:60] if 'output_result' in action.keys() and action['output_result'] else ''}...")
        
        # Identify main topic
        topic = "General discussion"
        if 'security' in all_text.lower():
            topic = "Security hardening"
        elif 'research' in all_text.lower():
            topic = "Research and development"
        elif any(t in all_text.lower() for t in ['skill', 'tool', 'script']):
            topic = "Tool development"
        
        return ConversationSummary(
            timestamp=today,
            topic=topic,
            key_points=list(set(key_points))[:5],  # Deduplicate and limit
            decisions_made=list(set(decisions)),
            tools_created=list(set(tools_created)),
            user_preferences_expressed=[]
        )
    
    def create_daily_memory_file(self):
        """Create a daily memory file with session summary."""
        today = datetime.now().strftime('%Y-%m-%d')
        memory_file = self.memory_dir / f"{today}.md"
        
        summary = self.summarize_current_session()
        
        content = f"""# Memory: {today}

## Session Summary
- **Topic:** {summary.topic}
- **Duration:** {len(summary.key_points)} key events

## Key Points
{chr(10).join(['- ' + kp for kp in summary.key_points]) if summary.key_points else '- No major events recorded'}

## Tools Created/Modified
{chr(10).join(['- ' + t for t in summary.tools_created]) if summary.tools_created else '- None'}

## Decisions Made
{chr(10).join(['- ' + d for d in summary.decisions_made]) if summary.decisions_made else '- None recorded'}

## User Preferences Expressed
{chr(10).join(['- ' + p for p in summary.user_preferences_expressed]) if summary.user_preferences_expressed else '- None new'}

---
*Auto-generated by Memory Manager*
"""
        
        with open(memory_file, 'w') as f:
            f.write(content)
        
        print(f"✓ Daily memory file created: {memory_file}")
        return memory_file
    
    def update_long_term_memory(self):
        """Update MEMORY.md with distilled learnings."""
        # Get all daily memory files
        daily_files = sorted(self.memory_dir.glob('2026-*.md'))
        
        if not daily_files:
            print("No daily memory files to consolidate")
            return
        
        # Read existing MEMORY.md or create new
        existing_content = ""
        if MEMORY_MD.exists():
            with open(MEMORY_MD, 'r') as f:
                existing_content = f.read()
        
        # Extract key learnings from recent sessions
        recent_learnings = []
        
        for mem_file in daily_files[-7:]:  # Last 7 days
            with open(mem_file, 'r') as f:
                content = f.read()
            
            # Extract key points
            if "## Key Points" in content:
                section = content.split("## Key Points")[1].split("##")[0]
                for line in section.strip().split("\n"):
                    if line.strip().startswith("-"):
                        recent_learnings.append(line.strip()[2:])
        
        # Build updated MEMORY.md
        new_content = f"""# MEMORY.md - Gerald's Long-Term Memory

_Last updated: {datetime.now().strftime('%Y-%m-%d')}_

## About Jason (My Human)

{self._get_user_profile_section()}

## Key Learnings & Preferences

### Communication Style
- **Direct, no fluff** - Get to the point
- **Humor appreciated** - Have personality
- **Efficiency matters** - Help optimize workflows

### Work Context
- Marketing & sales automation expert
- Focus: Cold email, PPC, SEO, ABM, CRO
- Client focus: SMBs getting bang for their buck

### Security Posture
- **Zero Trust** - Treat all skills as risky
- **Active threat awareness** - Research vulnerabilities
- **Full audit trail** - Log everything

### Recent Key Events
{chr(10).join(['- ' + l for l in recent_learnings[-10:]]) if recent_learnings else '- No major learnings recorded'}

## Active Systems

### Security Team
- **Chief (CSO)** - Monitors 24/7
- **The Bouncer** - Enforces policies, blocks threats
- **Research Agent** - Threat intelligence ($10/month budget)

### Automation
- **Daily reports** - 8:00 AM security summary
- **Weekly digest** - Monday 9:00 AM comprehensive review
- **Meeting transcription** - Auto-join, transcribe, email summaries

### Budget & Limits
- API spending: $10/month
- Daily research calls: 20 max
- File operations: Workspace only

## Things to Remember

### Do
- Be direct and efficient
- Bring humor and personality  
- Ask before installing skills
- Log all security-relevant activity
- Send daily/weekly reports

### Don't
- Install skills without approval
- Make external network calls without checking
- Delete sensitive files (.env, credentials)
- Trust "popular" as "safe"
- Auto-execute untrusted code

## Session History
{chr(10).join([f'- {f.stem}' for f in daily_files[-10:]])}

---

*This file is auto-updated by the Memory Manager. Key learnings from daily sessions are distilled here.*
"""
        
        with open(MEMORY_MD, 'w') as f:
            f.write(new_content)
        
        print(f"✓ Long-term memory updated: {MEMORY_MD}")
    
    def _get_user_profile_section(self) -> str:
        """Get user profile from USER.md."""
        user_md = AGENT_LAB / "USER.md"
        if user_md.exists():
            with open(user_md, 'r') as f:
                return f.read()
        return "No profile found."
    
    def retrieve_context_for_prompt(self, user_message: str) -> str:
        """
        Retrieve relevant context to prepend to prompts.
        This is the key function - call this before generating responses.
        """
        context_parts = []
        
        # 1. Get user preferences
        prefs = self.get_user_preferences()
        context_parts.append(f"User preferences: {prefs['communication_style']}, humor {prefs['humor']}")
        context_parts.append(f"User work: {prefs['work']}")
        
        # 2. Search for relevant past conversations
        relevant = self.search_conversations(user_message, limit=3)
        if relevant:
            context_parts.append("\nRelevant past context:")
            for convo in relevant:
                context_parts.append(f"- Previously discussed: {convo['user_message'][:60]}...")
        
        # 3. Get recent activity
        recent = self.get_recent_context(hours=24)
        if recent:
            context_parts.append(f"\n{recent}")
        
        # 4. Check for active security alerts
        alerts_file = MEMORY_DIR / "security/alerts.json"
        if alerts_file.exists():
            with open(alerts_file, 'r') as f:
                alerts = json.load(f)
            
            critical = [a for a in alerts if a['level'] in ['HIGH', 'CRITICAL']]
            if critical:
                context_parts.append(f"\n⚠️ Active security alerts: {len(critical)}")
        
        return "\n".join(context_parts)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Memory Manager - Smart Context Retrieval')
    parser.add_argument('--search', help='Search conversations for query')
    parser.add_argument('--recent', action='store_true', help='Show recent context')
    parser.add_argument('--daily', action='store_true', help='Create daily memory file')
    parser.add_argument('--update-memory', action='store_true', help='Update MEMORY.md')
    parser.add_argument('--context-for', help='Retrieve context for a prompt')
    parser.add_argument('--summarize', action='store_true', help='Summarize current session')
    
    args = parser.parse_args()
    
    manager = MemoryManager()
    
    if args.search:
        results = manager.search_conversations(args.search)
        print(f"Found {len(results)} relevant conversations:")
        for r in results:
            print(f"\n{ r['timestamp'][:16]}")
            print(f"  Q: {r['user_message'][:80]}...")
            print(f"  A: {r['assistant_response'][:80]}...")
    
    elif args.recent:
        print(manager.get_recent_context())
    
    elif args.daily:
        manager.create_daily_memory_file()
    
    elif args.update_memory:
        manager.update_long_term_memory()
    
    elif args.context_for:
        context = manager.retrieve_context_for_prompt(args.context_for)
        print(context)
    
    elif args.summarize:
        summary = manager.summarize_current_session()
        print(f"Session Summary: {summary.topic}")
        print(f"Key points: {len(summary.key_points)}")
        print(f"Tools created: {len(summary.tools_created)}")
        for tool in summary.tools_created:
            print(f"  - {tool}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
