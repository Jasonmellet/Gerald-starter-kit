#!/usr/bin/env python3
"""
Outreach Generator for X Leads
Drafts personalized DMs, replies, and emails for leads.

Usage:
  python3 tools/outreach_generator.py
  python3 tools/outreach_generator.py --lead @username
  python3 tools/outreach_generator.py --queue  # Queue for manual send
"""

import json
import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
LEAD_FILE = REPO_ROOT / "memory" / "x_lead_feed.json"
OUTREACH_FILE = REPO_ROOT / "memory" / "outreach_queue.json"

# Outreach templates by signal type
TEMPLATES = {
    "early_hire": [
        "Saw your tweet about {context}. I help early-stage startups build marketing systems that scale beyond that first hire. Worth a quick chat?",
        "Congrats on the {context}! I help startups set up marketing infrastructure so your team can hit the ground running. Interested?",
    ],
    "recent_funding": [
        "Saw you just raised funding — congrats! I help newly-funded startups build marketing systems that scale. Worth exploring?",
        "Post-funding marketing is critical. I help Series A/seed startups build systems that attract customers, not just investors. Let's chat?",
    ],
    "founder_voice": [
        "Great point about {context}. I work with early-stage founders on marketing systems that actually work. Let's connect.",
        "As a founder focused on {context}, you might find this interesting — I help startups like yours build marketing infrastructure. Worth a chat?",
    ],
    "active_marketing_need": [
        "Saw you're looking for marketing help. I specialize in helping early-stage startups build marketing systems, not just run campaigns. Interested?",
        "I help startups solve exactly that — {context}. Let's chat about what you're building.",
    ],
    "default": [
        "Saw your tweet about {context}. I help early-stage startups with marketing systems and growth. Worth connecting?",
    ]
}


def generate_outreach(lead):
    """Generate personalized outreach for a lead."""
    signals = lead.get("startup_signals", [])
    text = lead.get("text", "")
    username = lead.get("author_username", "")
    
    # Determine best template based on signals
    primary_signal = signals[0] if signals else "default"
    templates = TEMPLATES.get(primary_signal, TEMPLATES["default"])
    
    # Extract context from tweet
    context = extract_context(text)
    
    # Generate variations
    messages = []
    for template in templates[:2]:  # Use first 2 templates
        msg = template.format(context=context)
        messages.append(msg)
    
    return messages


def extract_context(text):
    """Extract key context from tweet for personalization."""
    text_lower = text.lower()
    
    if "first marketing hire" in text_lower or "first hire" in text_lower:
        return "making your first marketing hire"
    elif "raised" in text_lower or "funding" in text_lower or "seed" in text_lower or "series a" in text_lower:
        return "raising funding"
    elif "marketing" in text_lower and "help" in text_lower:
        return "marketing challenges"
    elif "growth" in text_lower:
        return "growth and scaling"
    elif "early stage" in text_lower:
        return "early-stage challenges"
    else:
        return "your startup journey"


def get_lead_email(username):
    """Try to find email for a lead (would need email finder integration)."""
    # Placeholder - would integrate with Hunter.io, Apollo, etc.
    return None


def queue_outreach(lead, messages):
    """Queue outreach for manual review and sending."""
    queue = []
    if OUTREACH_FILE.exists():
        queue = json.loads(OUTREACH_FILE.read_text())
    
    entry = {
        "queued_at": datetime.utcnow().isoformat() + "Z",
        "lead": lead,
        "messages": messages,
        "status": "pending_review",  # pending_review, approved, sent, rejected
        "channel": "x_dm",  # x_dm, x_reply, email
    }
    
    queue.append(entry)
    
    OUTREACH_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTREACH_FILE.write_text(json.dumps(queue, indent=2))
    
    return len(queue)


def generate_all_outreach():
    """Generate outreach for all leads in the feed."""
    if not LEAD_FILE.exists():
        print("No lead feed found. Run: python3 tools/x_lead_feed.py")
        return
    
    data = json.loads(LEAD_FILE.read_text())
    leads = data.get("leads", [])
    
    if not leads:
        print("No leads found.")
        return
    
    print(f"Generating outreach for {len(leads)} leads...")
    print("="*70)
    
    for lead in leads:
        username = lead.get("author_username", "")
        score = lead.get("startup_score", 0)
        signals = lead.get("startup_signals", [])
        
        messages = generate_outreach(lead)
        
        print(f"\n@{username} (Score: {score})")
        print(f"Signals: {', '.join(signals)}")
        print(f"Tweet: {lead.get('text', '')[:100]}...")
        print(f"\nSuggested outreach:")
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. {msg}")
        print(f"\nLink: {lead.get('link', '')}")
        print("-"*70)
        
        # Queue for review
        queue_outreach(lead, messages)
    
    print(f"\n✓ Queued {len(leads)} outreach messages for review")
    print(f"  File: {OUTREACH_FILE}")
    print(f"\nTo review and send:")
    print(f"  1. Read {OUTREACH_FILE}")
    print(f"  2. Copy messages and send manually via X DM/reply")
    print(f"  3. Or ask me to send via API (requires X DM permissions)")


def show_queue():
    """Show current outreach queue."""
    if not OUTREACH_FILE.exists():
        print("No outreach queue found.")
        return
    
    queue = json.loads(OUTREACH_FILE.read_text())
    pending = [q for q in queue if q.get("status") == "pending_review"]
    
    print(f"Outreach Queue: {len(pending)} pending")
    print("="*70)
    
    for entry in pending[:5]:  # Show first 5
        lead = entry.get("lead", {})
        messages = entry.get("messages", [])
        
        print(f"\n@{lead.get('author_username', 'unknown')}")
        print(f"Signals: {', '.join(lead.get('startup_signals', []))}")
        if messages:
            print(f"Suggested: {messages[0][:80]}...")
        print(f"Link: {lead.get('link', '')}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", action="store_true", help="Show outreach queue")
    args = parser.parse_args()
    
    if args.queue:
        show_queue()
    else:
        generate_all_outreach()
