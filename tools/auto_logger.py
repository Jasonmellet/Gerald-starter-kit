"""
Auto-logger for Gerald
Import this in your main agent code to automatically log conversations and actions.
"""

import os
import sys
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from logger import (
    log_conversation,
    log_action,
    start_session,
    end_session,
    init_database
)

# Ensure DB is initialized
init_database()

# Session tracking
_current_session = None


def get_session_id() -> str:
    """Get or create current session ID."""
    global _current_session
    if _current_session is None:
        _current_session = str(uuid.uuid4())[:8]
        start_session(_current_session)
    return _current_session


def log_user_message(message: str, channel: str = 'webchat'):
    """Log a user message (response will be logged separately)."""
    session_id = get_session_id()
    # Store temporarily - we'll pair with response
    log_action(
        action_type='user_message',
        input_params={'message': message[:500]},  # Truncate long messages
        session_id=session_id,
        metadata={'channel': channel}
    )


def log_assistant_response(response: str, channel: str = 'webchat'):
    """Log assistant response."""
    session_id = get_session_id()
    log_action(
        action_type='assistant_response',
        output_result=response[:1000],  # Truncate
        session_id=session_id,
        metadata={'channel': channel}
    )


def log_tool_call(tool_name: str, params: dict, result: str = None, success: bool = True):
    """Log a tool/function call."""
    session_id = get_session_id()
    log_action(
        action_type='tool_call',
        tool_name=tool_name,
        input_params=params,
        output_result=result[:500] if result else None,
        success=success,
        session_id=session_id
    )


def log_api_call(api_name: str, endpoint: str, cost: float = None, success: bool = True):
    """Log an external API call."""
    session_id = get_session_id()
    log_action(
        action_type='api_call',
        tool_name=api_name,
        input_params={'endpoint': endpoint},
        success=success,
        session_id=session_id,
        metadata={'cost': cost}
    )


def log_email_sent(to: str, subject: str, success: bool = True):
    """Log an email being sent."""
    session_id = get_session_id()
    log_action(
        action_type='email_sent',
        input_params={'to': to, 'subject': subject},
        success=success,
        session_id=session_id
    )


def log_file_operation(operation: str, file_path: str, success: bool = True):
    """Log a file read/write/edit operation."""
    session_id = get_session_id()
    log_action(
        action_type='file_operation',
        tool_name=operation,
        input_params={'file': file_path},
        success=success,
        session_id=session_id
    )


def log_research_query(query: str, results_count: int, cost: float):
    """Log a research query."""
    session_id = get_session_id()
    log_action(
        action_type='research_query',
        input_params={'query': query},
        output_result=f'Found {results_count} results',
        success=True,
        session_id=session_id,
        metadata={'cost': cost, 'results_count': results_count}
    )


def end_current_session(summary: str = None):
    """End the current session."""
    global _current_session
    if _current_session:
        end_session(_current_session, summary)
        _current_session = None
