#!/usr/bin/env python3
"""
Email Sender Tool for OpenClaw
Send emails from gerald@allgreatthings.io
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from gmail_client import GmailClient


def send_email(to: str, subject: str, body: str, html: bool = False) -> str:
    """
    Send an email using Gmail API.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
        html: Whether body is HTML (default: False for plain text)

    Returns:
        Message ID of sent email
    """
    client = GmailClient()

    # Authenticate with send permissions
    print("Authenticating with Gmail...")
    client.authenticate_with_send()
    print(f"Authenticated as: {client.email_address}")

    # Send email
    print(f"Sending email to: {to}")
    result = client.send_email(to=to, subject=subject, body=body, html=html)

    message_id = result.get('id', 'unknown')
    print(f"✓ Email sent successfully! Message ID: {message_id}")
    return message_id


def send_meeting_summary(meeting_file: str, to: str = "jason@allgreatthings.io"):
    """
    Send a meeting summary email.

    Args:
        meeting_file: Path to meeting summary .md file
        to: Recipient email address
    """
    import json

    # Read the summary file
    path = Path(meeting_file)
    if not path.exists():
        # Try in memory/meetings/
        path = Path("memory/meetings") / meeting_file
        if not path.exists():
            raise FileNotFoundError(f"Meeting file not found: {meeting_file}")

    # Read markdown content
    with open(path, 'r') as f:
        summary_content = f.read()

    # Try to find corresponding JSON for metadata
    json_path = path.with_suffix('.json')
    if not json_path.exists():
        json_path = Path(str(path).replace('_summary.md', '_analysis.json'))

    subject = "Meeting Summary"
    if json_path.exists():
        with open(json_path, 'r') as f:
            data = json.load(f)
            meeting_name = data.get('meeting_name', 'Meeting')
            meeting_date = data.get('meeting_date', '')
            subject = f"Meeting Summary: {meeting_name}"
            if meeting_date:
                subject += f" ({meeting_date})"

    # Send as HTML for better formatting
    # Convert markdown to simple HTML
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 25px; }}
        h3 {{ color: #7f8c8d; }}
        code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }}
        pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #3498db; margin: 0; padding-left: 15px; color: #555; }}
        ul, ol {{ padding-left: 20px; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
    </style>
</head>
<body>
{markdown_to_html(summary_content)}
<hr>
<p><em>Sent by Gerald 🤖</em></p>
</body>
</html>"""

    return send_email(to=to, subject=subject, body=html_body, html=True)


def markdown_to_html(markdown: str) -> str:
    """Simple markdown to HTML converter."""
    import re

    html = markdown

    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Code blocks
    html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

    # Blockquotes
    lines = html.split('\n')
    in_quote = False
    new_lines = []
    for line in lines:
        if line.startswith('> '):
            if not in_quote:
                new_lines.append('<blockquote>')
                in_quote = True
            new_lines.append(line[2:])
        else:
            if in_quote:
                new_lines.append('</blockquote>')
                in_quote = False
            new_lines.append(line)
    if in_quote:
        new_lines.append('</blockquote>')
    html = '\n'.join(new_lines)

    # Lists (simple)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.+</li>\n?)+', r'<ul>\g<0></ul>', html)

    # Links
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

    # Paragraphs (wrap lines not already in tags)
    lines = html.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<') and not stripped.endswith('>'):
            new_lines.append(f'<p>{line}</p>')
        else:
            new_lines.append(line)
    html = '\n'.join(new_lines)

    return html


def main():
    parser = argparse.ArgumentParser(description='Send emails from Gerald')
    parser.add_argument('--to', default='jason@allgreatthings.io',
                        help='Recipient email address')
    parser.add_argument('--subject', '-s',
                        help='Email subject (required unless using --meeting)')
    parser.add_argument('--body', '-b',
                        help='Email body (or use --file)')
    parser.add_argument('--file', '-f',
                        help='File containing email body')
    parser.add_argument('--html', action='store_true',
                        help='Send as HTML email')
    parser.add_argument('--meeting', '-m',
                        help='Send a meeting summary file')

    args = parser.parse_args()

    # Validate: subject is required unless using --meeting
    if not args.meeting and not args.subject:
        parser.error('--subject is required unless using --meeting')

    try:
        if args.meeting:
            send_meeting_summary(args.meeting, to=args.to)
        elif args.file:
            with open(args.file, 'r') as f:
                body = f.read()
            send_email(to=args.to, subject=args.subject, body=body, html=args.html)
        elif args.body:
            send_email(to=args.to, subject=args.subject, body=args.body, html=args.html)
        else:
            # Read from stdin
            print("Enter email body (Ctrl+D to finish):")
            body = sys.stdin.read()
            send_email(to=args.to, subject=args.subject, body=body, html=args.html)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
