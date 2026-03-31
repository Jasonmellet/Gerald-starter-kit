"""
Gmail API client. OAuth, calendar invites, send email.
"""
import os
import base64
import pickle
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GmailClient:
    SCOPES_READ = ["https://www.googleapis.com/auth/gmail.readonly"]
    SCOPES_SEND = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        use_send_scope: bool = True,
    ):
        if not GOOGLE_AVAILABLE:
            raise RuntimeError(
                "Install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
        self.credentials_path = credentials_path or os.getenv("GMAIL_CREDENTIALS_PATH", "")
        self.token_path = token_path or os.getenv("GMAIL_TOKEN_PATH", "")
        if not self.credentials_path or not self.token_path:
            raise ValueError("GMAIL_CREDENTIALS_PATH and GMAIL_TOKEN_PATH (or constructor args) required")
        self.service = None
        self.email_address = None
        self._scopes = self.SCOPES_SEND if use_send_scope else self.SCOPES_READ

    def authenticate(self) -> bool:
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as f:
                creds = pickle.load(f)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials not found: {self.credentials_path}\n"
                        "Put gmail-credentials.json in meeting_bot/credentials/"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self._scopes
                )
                flow.redirect_uri = "http://localhost:8080"
                creds = flow.run_local_server(port=8080)
            Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, "wb") as f:
                pickle.dump(creds, f)
        self.service = build("gmail", "v1", credentials=creds)
        profile = self.service.users().getProfile(userId="me").execute()
        self.email_address = profile.get("emailAddress")
        return True

    def is_authenticated(self) -> bool:
        return self.service is not None

    def get_calendar_invites(self, max_results: int = 50) -> List[Dict[str, Any]]:
        if not self.is_authenticated():
            raise RuntimeError("Authenticate first")
        invites = []
        query = "filename:.ics OR subject:(invited you to) OR subject:(calendar invitation)"
        try:
            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
            for msg_meta in results.get("messages", []):
                msg = self.service.users().messages().get(
                    userId="me", id=msg_meta["id"], format="full"
                ).execute()
                invite = self._parse_invite(msg)
                if invite:
                    invites.append(invite)
        except HttpError as e:
            print(f"Error fetching invites: {e}")
        return invites

    def _parse_invite(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        headers = msg.get("payload", {}).get("headers", [])
        subject = self._get_header(headers, "Subject", "No Subject")
        message_id = msg.get("id")
        ics_data = None
        for part in msg.get("payload", {}).get("parts", []):
            if (part.get("filename") or "").endswith(".ics"):
                body = part.get("body", {})
                if "data" in body:
                    ics_data = base64.urlsafe_b64decode(body["data"]).decode("utf-8")
                elif body.get("attachmentId"):
                    att = self.service.users().messages().attachments().get(
                        userId="me", messageId=message_id, id=body["attachmentId"]
                    ).execute()
                    ics_data = base64.urlsafe_b64decode(att["data"]).decode("utf-8")
                break
        meeting_info = self._parse_ics(ics_data) if ics_data else {}
        meeting_url = meeting_info.get("meeting_url") or self._extract_meeting_url(msg)
        if not meeting_url:
            return None
        return {
            "message_id": message_id,
            "subject": subject,
            "meeting_url": meeting_url,
            "start_time": meeting_info.get("start_time"),
            "end_time": meeting_info.get("end_time"),
            "organizer": meeting_info.get("organizer"),
            "attendees": meeting_info.get("attendees", []),
        }

    def _get_header(self, headers: List[Dict], name: str, default: str = "") -> str:
        for h in headers:
            if h.get("name") == name:
                return h.get("value", default)
        return default

    def _ical_datetime_to_iso(self, value: str) -> Optional[str]:
        if not value or len(value) < 15:
            return None
        raw = value.split(":")[-1].strip()
        if not raw:
            return None
        is_utc = raw.endswith("Z")
        if is_utc:
            raw = raw[:-1]
        if len(raw) >= 15 and "T" in raw:
            try:
                date_part, time_part = raw.split("T", 1)
                y, m, d = date_part[:4], date_part[4:6], date_part[6:8]
                h = time_part[:2] if len(time_part) >= 2 else "00"
                mi = time_part[2:4] if len(time_part) >= 4 else "00"
                s = time_part[4:6] if len(time_part) >= 6 else "00"
                iso = f"{y}-{m}-{d}T{h}:{mi}:{s}"
                return iso + "+00:00" if is_utc else iso
            except Exception:
                pass
        return None

    def _parse_ics(self, ics_data: str) -> Dict[str, Any]:
        info = {}
        lines = ics_data.split("\n")
        in_vevent = False
        for line in lines:
            line = line.strip()
            if line == "BEGIN:VEVENT":
                in_vevent = True
            elif line == "END:VEVENT":
                in_vevent = False
            elif in_vevent:
                if line.startswith("DTSTART"):
                    raw = line[line.rfind(":") + 1:] if ":" in line else ""
                    iso = self._ical_datetime_to_iso(raw)
                    if iso:
                        info["start_time"] = iso
                elif line.startswith("DTEND"):
                    raw = line[line.rfind(":") + 1:] if ":" in line else ""
                    iso = self._ical_datetime_to_iso(raw)
                    if iso:
                        info["end_time"] = iso
                elif "mailto:" in line and line.startswith("ORGANIZER"):
                    info["organizer"] = line.split("mailto:")[-1]
                elif "mailto:" in line and line.startswith("ATTENDEE"):
                    info.setdefault("attendees", []).append(line.split("mailto:")[-1])
                elif line.startswith("LOCATION:"):
                    loc = line.replace("LOCATION:", "").strip()
                    if loc.startswith("http"):
                        info["meeting_url"] = loc
        return info

    def _extract_meeting_url(self, msg: Dict[str, Any]) -> Optional[str]:
        body = self._get_message_body(msg)
        if not body:
            return None
        patterns = [
            r"https://[\w\-]*\.zoom\.us/j/\d+\?pwd=[\w\-]+",
            r"https://[\w\-]*\.zoom\.us/j/\d+",
            r"https://meet\.google\.com/[a-z\-]+",
            r"https://teams\.microsoft\.com/l/meetup-join/[\w\-%]+",
        ]
        for pattern in patterns:
            m = re.search(pattern, body, re.IGNORECASE)
            if m:
                return m.group(0)
        return None

    def _get_message_body(self, msg: Dict[str, Any]) -> str:
        parts = msg.get("payload", {}).get("parts", [msg.get("payload", {})])
        body = ""
        for part in parts:
            mt = part.get("mimeType", "")
            data = part.get("body", {}).get("data", "")
            if not data:
                continue
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            if mt == "text/plain":
                body += decoded
            elif mt == "text/html":
                body += re.sub(r"<[^>]+>", " ", decoded)
        return body

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        if not self.is_authenticated():
            raise RuntimeError("Authenticate first (with send scope)")
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        message = MIMEMultipart("alternative")
        message["to"] = to
        message["from"] = self.email_address
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return self.service.users().messages().send(userId="me", body={"raw": raw}).execute()
