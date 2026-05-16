import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import os
import re
from datetime import datetime

# ─────────────────────────────────────────────
# EMAIL CONFIG  (add these to your .env file)
# EMAIL_ADDRESS=your_gmail@gmail.com
# EMAIL_PASSWORD=your_app_password   ← Gmail App Password (not your real password)
# IMAP_SERVER=imap.gmail.com
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# ─────────────────────────────────────────────

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
IMAP_SERVER   = os.getenv("IMAP_SERVER", "imap.gmail.com")
SMTP_SERVER   = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))


# ──────────────────────────────
# HELPERS
# ──────────────────────────────

def _decode_str(value):
    """Decode an encoded email header value to plain string."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _get_body(msg):
    """Extract plain-text body from an email.Message object."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                charset = part.get_content_charset() or "utf-8"
                body = part.get_payload(decode=True).decode(charset, errors="replace")
                break
    else:
        charset = msg.get_content_charset() or "utf-8"
        body = msg.get_payload(decode=True).decode(charset, errors="replace")
    return body.strip()


def _connect_imap():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    return mail


# ──────────────────────────────
# TOOL FUNCTIONS
# ──────────────────────────────

def get_unread_emails(max_count: int = 5) -> str:
    """
    Fetch unread emails from Gmail inbox.
    Returns a formatted summary string the voice agent can speak.
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email credentials are not configured. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in your .env file."

    try:
        mail = _connect_imap()
        mail.select("inbox")

        _, data = mail.search(None, "UNSEEN")
        ids = data[0].split()

        if not ids:
            mail.logout()
            return "You have no unread emails."

        # Take the most recent N
        ids = ids[-max_count:]
        summaries = []

        for uid in reversed(ids):
            _, msg_data = mail.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            sender  = _decode_str(msg.get("From", "Unknown"))
            subject = _decode_str(msg.get("Subject", "(No Subject)"))
            date    = msg.get("Date", "")
            body    = _get_body(msg)[:200]          # first 200 chars for voice

            summaries.append(
                f"From: {sender}\nSubject: {subject}\nDate: {date}\nPreview: {body}"
            )

        mail.logout()
        count = len(summaries)
        result = f"You have {count} unread email{'s' if count > 1 else ''}.\n\n"
        result += "\n\n---\n\n".join(summaries)
        return result

    except Exception as e:
        return f"Error reading emails: {str(e)}"


def read_latest_email() -> str:
    """
    Read the single most recent email (read or unread) from inbox.
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email credentials are not configured."

    try:
        mail = _connect_imap()
        mail.select("inbox")

        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        if not ids:
            mail.logout()
            return "Your inbox is empty."

        uid = ids[-1]
        _, msg_data = mail.fetch(uid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        sender  = _decode_str(msg.get("From", "Unknown"))
        subject = _decode_str(msg.get("Subject", "(No Subject)"))
        date    = msg.get("Date", "")
        body    = _get_body(msg)[:500]

        mail.logout()
        return (
            f"Latest email:\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Date: {date}\n\n"
            f"{body}"
        )

    except Exception as e:
        return f"Error reading email: {str(e)}"


def search_emails(query: str, max_count: int = 5) -> str:
    """
    Search emails by subject or sender keyword.
    query: keyword to search for (searches Subject and From headers)
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email credentials are not configured."

    try:
        mail = _connect_imap()
        mail.select("inbox")

        # Search subject and from separately, combine results
        _, subj_data = mail.search(None, f'SUBJECT "{query}"')
        _, from_data = mail.search(None, f'FROM "{query}"')

        subj_ids = set(subj_data[0].split())
        from_ids = set(from_data[0].split())
        all_ids  = list(subj_ids | from_ids)

        if not all_ids:
            mail.logout()
            return f"No emails found matching '{query}'."

        all_ids = all_ids[-max_count:]
        summaries = []

        for uid in all_ids:
            _, msg_data = mail.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            sender  = _decode_str(msg.get("From", "Unknown"))
            subject = _decode_str(msg.get("Subject", "(No Subject)"))
            date    = msg.get("Date", "")

            summaries.append(f"From: {sender} | Subject: {subject} | Date: {date}")

        mail.logout()
        return f"Found {len(summaries)} email(s) matching '{query}':\n\n" + "\n".join(summaries)

    except Exception as e:
        return f"Error searching emails: {str(e)}"


def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email via Gmail SMTP.
    to:      recipient email address
    subject: email subject line
    body:    plain-text email body
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email credentials are not configured. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in your .env file."

    # Basic validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", to):
        return f"Invalid email address: {to}"

    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_ADDRESS
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to, msg.as_string())

        return f"Email sent successfully to {to} with subject '{subject}'."

    except smtplib.SMTPAuthenticationError:
        return "Authentication failed. Check your EMAIL_PASSWORD (use a Gmail App Password, not your real password)."
    except smtplib.SMTPRecipientsRefused:
        return f"Recipient address '{to}' was refused by the server."
    except Exception as e:
        return f"Error sending email: {str(e)}"


def get_email_count() -> str:
    """Return count of unread emails — quick check for voice agent."""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email credentials are not configured."
    try:
        mail = _connect_imap()
        mail.select("inbox")
        _, data = mail.search(None, "UNSEEN")
        ids = data[0].split()
        mail.logout()
        count = len(ids)
        if count == 0:
            return "You have no unread emails."
        elif count == 1:
            return "You have 1 unread email."
        else:
            return f"You have {count} unread emails."
    except Exception as e:
        return f"Error checking email count: {str(e)}"