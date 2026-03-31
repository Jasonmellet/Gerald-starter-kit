#!/usr/bin/env python3
"""
Sessions Send - Send messages to any configured channel
Used by skills and tools to send notifications to users.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def sessions_send(recipient, message):
    """
    Send a message to a specific channel/session.
    
    Args:
        recipient: Channel identifier (e.g., 'telegram:8130598479' or just '8130598479')
        message: Message text to send
    """
    # Normalize recipient
    if ':' not in recipient:
        # Assume Telegram if no prefix
        recipient = f"telegram:{recipient}"
    
    try:
        # Use openclaw CLI to send message
        result = subprocess.run(
            ['openclaw', 'sessions', 'send', recipient, message],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✓ Message sent to {recipient}")
            return True
        else:
            print(f"✗ Failed to send message: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error sending message: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Send message to a channel')
    parser.add_argument('recipient', help='Recipient (e.g., telegram:12345)')
    parser.add_argument('message', help='Message to send')
    
    args = parser.parse_args()
    
    success = sessions_send(args.recipient, args.message)
    sys.exit(0 if success else 1)
