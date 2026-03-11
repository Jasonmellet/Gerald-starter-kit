#!/usr/bin/env python3
"""
Recall.ai cleanup: leave all running bots (free slots) and optionally try to delete completed ones.

  python3 tools/recall_cleanup.py          # Leave all running bots, then try to delete completed
  python3 tools/recall_cleanup.py --leave  # Only tell every running bot to leave the call
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


load_env()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from recall_client import RecallAIClient

# Terminal = already ended; no need to leave
TERMINAL_STATUSES = {
    "done", "fatal", "call_ended", "analysis_done", "analysis_failed",
    "media_expired", "failed", "kicked", "left", "cancelled", "error",
}


def main():
    p = argparse.ArgumentParser(description="Recall.ai: leave running bots and/or delete completed")
    p.add_argument("--leave", action="store_true", help="Only send leave_call to all running bots (default: leave + try delete)")
    args = p.parse_args()
    leave_only = args.leave

    print("Recall.ai cleanup\n")
    try:
        client = RecallAIClient()
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    bots = client.list_bots()
    print(f"Total bots on Recall: {len(bots)}")
    status_counts = {}
    for b in bots:
        s = b.get("status") or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
    print("Status breakdown:", status_counts)

    # 1) Leave all running (non-terminal) bots so they stop using slots
    to_leave = [b for b in bots if (b.get("status") or "").lower() not in TERMINAL_STATUSES]
    if to_leave:
        print(f"\nSending leave_call to {len(to_leave)} running bot(s)...")
        left = 0
        for b in to_leave:
            bid = b.get("id")
            status = b.get("status", "?")
            try:
                if client.leave_call(bid):
                    print(f"  Left {bid[:8]}... (status={status})")
                    left += 1
                else:
                    print(f"  Could not leave {bid[:8]}... (status={status})")
            except Exception as e:
                print(f"  Error leaving {bid[:8]}...: {e}")
        print(f"  Sent leave to {left} bot(s). They will transition to 'done' and free slots shortly.")
    else:
        print("\nNo running bots to leave (all are already in a terminal state).")

    if leave_only:
        return 0

    # 2) Try to delete completed bots (Recall often disallows this; leave_call above is what frees slots)
    to_delete = [b for b in bots if (b.get("status") or "").lower() in TERMINAL_STATUSES]
    if not to_delete:
        return 0
    print(f"\nAttempting to delete {len(to_delete)} completed bot(s)...")
    deleted = 0
    for b in to_delete:
        bid = b.get("id")
        status = b.get("status", "?")
        try:
            if client.delete_bot(bid):
                print(f"  Deleted {bid[:8]}... (status={status})")
                deleted += 1
            else:
                pass  # Recall often returns 405 for completed bots; leave_call is what freed the slot
        except Exception as e:
            print(f"  Error deleting {bid[:8]}...: {e}")
    if deleted:
        print(f"  Deleted {deleted} bot(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
