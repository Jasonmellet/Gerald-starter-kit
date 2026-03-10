"""
Gmail API Client for OpenClaw
Handles OAuth authentication and calendar invite monitoring.
"""

import os
import json
import base64
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from email.utils import parsedate_to_datetime

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
    print("Warning: Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


class GmailClient:
    """Client for monitoring Gmail inbox and sending emails."""

    # Gmail API scopes - read-only access to inbox (default)
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    # Extended scope for sending emails
    SCOPES_SEND = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize Gmail client.
        
        Args:
            credentials_path: Path to OAuth client credentials JSON
            token_path: Path to store/fetch OAuth tokens
        """
        if not GOOGLE_LIBS_AVAILABLE:
            raise RuntimeError("Google API libraries required. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        
        self.credentials_path = credentials_path or os.getenv(
            "GMAIL_CREDENTIALS_PATH", 
            "credentials/gmail-credentials.json"
        )
        self.token_path = token_path or "credentials/gmail-token.pickle"
        self.service = None
        self.email_address = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth.
        
        Returns:
            True if authentication successful
            
        Note:
            First time will open browser for user consent.
        """
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        "Please ensure gmail-credentials.json is in the credentials/ folder"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path,
                    self.SCOPES
                )
                # Use port 8080 (no root needed). Desktop app allows localhost; we send this redirect_uri.
                flow.redirect_uri = "http://localhost:8080"
                creds = flow.run_local_server(port=8080)
            
            # Save credentials for future runs
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build service
        self.service = build('gmail', 'v1', credentials=creds)
        
        # Get email address
        profile = self.service.users().getProfile(userId='me').execute()
        self.email_address = profile.get('emailAddress')
        
        return True
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.service is not None
    
    def get_calendar_invites(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for calendar invitation emails.
        
        Args:
            max_results: Maximum number of invites to return
            
        Returns:
            List of invite dictionaries with meeting details
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        invites = []
        
        # Search for calendar invites
        # Gmail query: look for .ics attachments or calendar invite patterns
        query = "filename:.ics OR subject:(invited you to) OR subject:(calendar invitation)"
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            for msg_meta in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=msg_meta['id'],
                    format='full'
                ).execute()
                
                invite = self._parse_invite(msg)
                if invite:
                    invites.append(invite)
            
            return invites
            
        except HttpError as e:
            print(f"Error fetching messages: {e}")
            return []
    
    def _parse_invite(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a Gmail message to extract calendar invite details."""
        headers = msg.get('payload', {}).get('headers', [])
        
        # Extract basic info
        subject = self._get_header(headers, 'Subject', 'No Subject')
        sender = self._get_header(headers, 'From', 'Unknown')
        date_str = self._get_header(headers, 'Date', '')
        message_id = msg.get('id')
        
        # Look for .ics attachment
        ics_data = None
        parts = msg.get('payload', {}).get('parts', [])
        
        for part in parts:
            filename = part.get('filename', '')
            if filename.endswith('.ics'):
                # Download attachment
                if 'data' in part.get('body', {}):
                    data = part['body']['data']
                else:
                    att_id = part['body'].get('attachmentId')
                    if att_id:
                        att = self.service.users().messages().attachments().get(
                            userId='me',
                            messageId=message_id,
                            id=att_id
                        ).execute()
                        data = att['data']
                    else:
                        continue
                
                ics_data = base64.urlsafe_b64decode(data).decode('utf-8')
                break
        
        # Parse .ics for meeting details
        meeting_info = self._parse_ics(ics_data) if ics_data else {}
        
        # Extract meeting URL from body or location
        meeting_url = meeting_info.get('meeting_url') or self._extract_meeting_url(msg)
        
        if not meeting_url:
            return None  # Skip if no meeting URL found
        
        return {
            'message_id': message_id,
            'subject': subject,
            'sender': sender,
            'date': date_str,
            'meeting_url': meeting_url,
            'start_time': meeting_info.get('start_time'),
            'end_time': meeting_info.get('end_time'),
            'organizer': meeting_info.get('organizer'),
            'attendees': meeting_info.get('attendees', []),
            'ics_data': ics_data
        }
    
    def _get_header(self, headers: List[Dict], name: str, default: str = '') -> str:
        """Extract header value by name."""
        for header in headers:
            if header.get('name') == name:
                return header.get('value', default)
        return default
    
    def _parse_ics(self, ics_data: str) -> Dict[str, Any]:
        """Parse iCalendar (.ics) data to extract meeting info."""
        info = {}
        lines = ics_data.split('\n')
        
        in_vevent = False
        for line in lines:
            line = line.strip()
            
            if line == 'BEGIN:VEVENT':
                in_vevent = True
            elif line == 'END:VEVENT':
                in_vevent = False
            elif in_vevent:
                if line.startswith('DTSTART:'):
                    info['start_time'] = line.replace('DTSTART:', '')
                elif line.startswith('DTEND:'):
                    info['end_time'] = line.replace('DTEND:', '')
                elif line.startswith('ORGANIZER'):
                    # Extract email from ORGANIZER;CN=Name:mailto:email@example.com
                    if 'mailto:' in line:
                        info['organizer'] = line.split('mailto:')[-1]
                elif line.startswith('ATTENDEE'):
                    if 'mailto:' in line:
                        attendee = line.split('mailto:')[-1]
                        info.setdefault('attendees', []).append(attendee)
                elif line.startswith('LOCATION:'):
                    location = line.replace('LOCATION:', '')
                    # Check if location is a URL
                    if location.startswith('http'):
                        info['meeting_url'] = location
        
        return info
    
    def _extract_meeting_url(self, msg: Dict[str, Any]) -> Optional[str]:
        """Extract meeting URL from message body."""
        # Get message body
        body = self._get_message_body(msg)
        if not body:
            return None
        
        # Look for common meeting patterns
        import re
        
        patterns = [
            # Zoom
            r'https://[\w\-]*\.zoom\.us/j/\d+\?pwd=[\w\-]+',
            r'https://[\w\-]*\.zoom\.us/j/\d+',
            # Google Meet
            r'https://meet\.google\.com/[a-z\-]+',
            # Microsoft Teams
            r'https://teams\.microsoft\.com/l/meetup-join/[\w\-%]+',
            r'https://[\w\-]+\.teams\.live\.com/meet/[\w\-]+',
            # Webex
            r'https://[\w\-]*\.webex\.com/meet/[\w\-]+',
            r'https://[\w\-]*\.webex\.com/join/[\w\-]+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _get_message_body(self, msg: Dict[str, Any]) -> str:
        """Extract text body from Gmail message."""
        parts = msg.get('payload', {}).get('parts', [msg.get('payload', {})])
        body = ""
        
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif mime_type == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    # Simple HTML to text
                    import re
                    body += re.sub(r'<[^>]+>', ' ', html)
        
        return body

    def authenticate_with_send(self) -> bool:
        """
        Authenticate with Gmail API including send permissions.

        Returns:
            True if authentication successful

        Note:
            First time will open browser for user consent.
            Requires gmail.send scope.
        """
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, get them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        "Please ensure gmail-credentials.json is in the credentials/ folder"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path,
                    self.SCOPES_SEND
                )
                # Use port 8080 (no root needed). Desktop app allows localhost; we send this redirect_uri.
                flow.redirect_uri = "http://localhost:8080"
                creds = flow.run_local_server(port=8080)

            # Save credentials for future runs
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        # Build service
        self.service = build('gmail', 'v1', credentials=creds)

        # Get email address
        profile = self.service.users().getProfile(userId='me').execute()
        self.email_address = profile.get('emailAddress')

        return True

    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> Dict[str, Any]:
        """
        Send an email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            html: If True, body is treated as HTML; otherwise plain text

        Returns:
            API response with message ID

        Raises:
            RuntimeError: If not authenticated with send permissions
        """
        if not self.is_authenticated():
            raise RuntimeError("Not authenticated. Call authenticate_with_send() first.")

        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Create message
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['from'] = self.email_address
        message['subject'] = subject

        # Attach body
        content_type = 'html' if html else 'plain'
        message.attach(MIMEText(body, content_type))

        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        try:
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            return result
        except HttpError as e:
            raise RuntimeError(f"Failed to send email: {e}")


def test_authentication():
    """Test Gmail authentication."""
    try:
        client = GmailClient()
        if client.authenticate():
            print(f"✓ Gmail authentication successful: {client.email_address}")
            return True
    except Exception as e:
        print(f"✗ Gmail authentication failed: {e}")
        return False


if __name__ == "__main__":
    test_authentication()
