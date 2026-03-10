#!/usr/bin/env python3
"""
Generate and send email digest of top-scored leads via Gmail API.
"""

import sqlite3
import json
import base64
import os
from pathlib import Path
from email.mime.text import MIMEText
from datetime import datetime

# Gmail API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("Warning: Gmail API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

DB_PATH = Path(__file__).parent.parent / 'data' / 'leads.db'
CONFIG_PATH = Path(__file__).parent.parent / 'config.json'
CREDENTIALS_PATH = Path('~/Desktop/Openclaw/credentials/gmail-credentials.json').expanduser()
TOKEN_PATH = Path('~/Desktop/Openclaw/credentials/gmail-token.pickle').expanduser()

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {
        'digest': {
            'to_email': 'jason@allgreatthings.io',
            'from_email': 'gerald@allgreatthings.io',
            'min_score': 70
        }
    }

def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None
    
    # Load existing token
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(f"Gmail credentials not found at {CREDENTIALS_PATH}")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token for future runs
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

def generate_pitch(lead: dict) -> str:
    """Generate a personalized pitch based on lead details."""
    company = lead['company'] or 'your company'
    
    if 'cmo' in lead['description'].lower() or 'marketing' in lead['description'].lower():
        return f"""Hi {lead['contact_name'] or 'there'},

I saw {company} is looking for marketing leadership. I'm a Fractional CMO who helps startups build their growth engine without the full-time hire overhead.

Recent wins:
- 3x'd pipeline for Series A SaaS in 90 days
- Built first marketing team for 2 startups
- Cut CAC by 40% through automation

Worth a 15-min chat to see if there's a fit?

Best,
Gerald"""
    else:
        return f"""Hi {lead['contact_name'] or 'there'},

Noticed {company} is exploring AI/automation. I build custom AI agents that handle the repetitive work so your team can focus on high-leverage activities.

Recent projects:
- Automated lead qualification saving 20 hrs/week
- Built content generation pipeline
- Created customer support bot handling 60% of tickets

Happy to show you what's possible in a quick demo.

Best,
Gerald"""

def generate_digest():
    config = load_config()
    min_score = config['digest'].get('min_score', 70)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM leads 
        WHERE status = 'new' AND score >= ? 
        ORDER BY score DESC 
        LIMIT 10
    """, (min_score,))
    
    leads = [dict(row) for row in cursor.fetchall()]
    
    if not leads:
        return None, "No high-scoring leads found."
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0;">🦞 Gerald's CRO Daily Digest</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.8;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
        </div>
        
        <div style="padding: 20px;">
            <p>Found <strong>{len(leads)} hot leads</strong> worth your attention:</p>
    """
    
    for lead in leads:
        pitch = generate_pitch(lead)
        
        # Determine badge color based on score
        if lead['score'] >= 80:
            badge_color = '#00d084'
            badge_text = '🔥 HOT'
        elif lead['score'] >= 70:
            badge_color = '#ffa500'
            badge_text = '⚡ WARM'
        else:
            badge_color = '#6c757d'
            badge_text = '💡 COOL'
        
        html += f"""
        <div style="border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; background: #fafafa;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #1a1a2e;">{lead['company'] or 'Unknown Company'}</h3>
                <span style="background: {badge_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold;">
                    {badge_text} ({lead['score']})
                </span>
            </div>
            
            <p style="margin: 5px 0; color: #666; font-size: 14px;">
                <strong>Source:</strong> {lead['source']} | 
                <strong>Contact:</strong> {lead['contact_name'] or 'N/A'} | 
                <strong>Role:</strong> {lead['title'] or 'N/A'}
            </p>
            
            <p style="margin: 15px 0; line-height: 1.6;">{lead['description'][:300]}...</p>
            
            {f'<p><a href="{lead["url"]}" style="color: #0066cc; text-decoration: none;">🔗 View Original Post →</a></p>' if lead['url'] else ''}
            
            <details style="margin-top: 15px;">
                <summary style="cursor: pointer; color: #0066cc; font-weight: bold; padding: 10px; background: #e9ecef; border-radius: 4px;">
                    📧 View Suggested Pitch
                </summary>
                <div style="background: white; padding: 15px; margin-top: 10px; border-radius: 4px; border-left: 4px solid #0066cc;">
                    <pre style="margin: 0; white-space: pre-wrap; font-family: monospace; font-size: 13px; line-height: 1.5;">{pitch}</pre>
                </div>
            </details>
        </div>
        """
    
    html += """
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #ddd;">
            <p style="margin: 0; font-size: 12px; color: #666;">
                Generated by Fractional CRO skill | 
                <a href="https://github.com/openclaw" style="color: #666;">OpenClaw</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    return html, None

def send_email_via_gmail(to_email, from_email, subject, html_body):
    """Send email using Gmail API."""
    if not GMAIL_AVAILABLE:
        raise ImportError("Gmail API libraries not available")
    
    service = get_gmail_service()
    
    # Create MIME message
    message = MIMEText(html_body, 'html')
    message['to'] = to_email
    message['from'] = from_email
    message['subject'] = subject
    
    # Encode and send
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    body = {'raw': raw_message}
    
    sent = service.users().messages().send(userId='me', body=body).execute()
    return sent['id']

def send_digest():
    config = load_config()
    digest_config = config['digest']
    
    html, error = generate_digest()
    if error:
        print(error)
        return
    
    to_email = digest_config.get('to_email', 'jason@allgreatthings.io')
    from_email = digest_config.get('from_email', 'gerald@allgreatthings.io')
    subject = f"🎯 CRO Daily Digest - {datetime.now().strftime('%Y-%m-%d')}"
    
    try:
        if GMAIL_AVAILABLE:
            message_id = send_email_via_gmail(to_email, from_email, subject, html)
            print(f"✅ Digest sent successfully!")
            print(f"   To: {to_email}")
            print(f"   Message ID: {message_id}")
            print(f"   Leads included: {html.count('<h3')}")
        else:
            # Fallback: save to file
            output_path = Path(__file__).parent.parent / 'data' / f"digest_{datetime.now().strftime('%Y%m%d')}.html"
            with open(output_path, 'w') as f:
                f.write(html)
            print(f"⚠️ Gmail API not available. Digest saved to {output_path}")
            
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        # Save fallback
        output_path = Path(__file__).parent.parent / 'data' / f"digest_{datetime.now().strftime('%Y%m%d')}.html"
        with open(output_path, 'w') as f:
            f.write(html)
        print(f"   Digest saved to {output_path}")

if __name__ == '__main__':
    send_digest()
