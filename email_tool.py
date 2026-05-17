"""
email_tool.py — Gmail API version (no SMTP, works on Railway)
"""
import os, re, base64, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import email as email_lib

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")

def _get_gmail_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_json = os.environ.get("GMAIL_TOKEN")
    if not token_json:
        raise RuntimeError("GMAIL_TOKEN environment variable not set.")
    creds = Credentials.from_authorized_user_info(json.loads(token_json))
    return build("gmail", "v1", credentials=creds)

def _decode_str(value):
    if not value: return ""
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)

def get_email_count() -> str:
    try:
        service = _get_gmail_service()
        result = service.users().messages().list(
            userId="me", labelIds=["INBOX", "UNREAD"], maxResults=1
        ).execute()
        count = result.get("resultSizeEstimate", 0)
        if count == 0: return "You have no unread emails."
        elif count == 1: return "You have 1 unread email."
        else: return f"You have {count} unread emails."
    except Exception as e:
        return f"Error checking email count: {e}"

def get_unread_emails(max_count: int = 5) -> str:
    try:
        service = _get_gmail_service()
        result = service.users().messages().list(
            userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_count
        ).execute()
        messages = result.get("messages", [])
        if not messages: return "You have no unread emails."

        summaries = []
        for m in messages:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            summaries.append(
                f"From: {headers.get('From','?')} | "
                f"Subject: {headers.get('Subject','(No Subject)')} | "
                f"Date: {headers.get('Date','?')}"
            )

        return f"You have {len(summaries)} unread emails:\n\n" + "\n".join(summaries)
    except Exception as e:
        return f"Error reading emails: {e}"

def send_email(to: str, subject: str, body: str) -> str:
    if not re.match(r"[^@]+@[^@]+\.[^@]+", to):
        return f"Invalid email address: {to}"
    try:
        service = _get_gmail_service()
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return f"Email sent successfully to {to} with subject '{subject}'."
    except Exception as e:
        return f"Error sending email: {e}"

def read_latest_email() -> str:
    try:
        service = _get_gmail_service()
        result = service.users().messages().list(
            userId="me", labelIds=["INBOX"], maxResults=1
        ).execute()
        messages = result.get("messages", [])
        if not messages: return "Your inbox is empty."
        msg = service.users().messages().get(
            userId="me", id=messages[0]["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        return (f"Latest email — From: {headers.get('From','?')} | "
                f"Subject: {headers.get('Subject','?')} | "
                f"Date: {headers.get('Date','?')}")
    except Exception as e:
        return f"Error reading email: {e}"

def search_emails(query: str, max_count: int = 5) -> str:
    try:
        service = _get_gmail_service()
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_count
        ).execute()
        messages = result.get("messages", [])
        if not messages: return f"No emails found matching '{query}'."
        summaries = []
        for m in messages:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            summaries.append(
                f"From: {headers.get('From','?')} | Subject: {headers.get('Subject','?')}"
            )
        return f"Found {len(summaries)} email(s):\n" + "\n".join(summaries)
    except Exception as e:
        return f"Error searching emails: {e}"