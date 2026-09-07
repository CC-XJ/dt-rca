#!/usr/bin/env python3
"""
Usage (as a script):
    python send_email.py \
        --to recipient@example.com \
        --cc manager@example.com \
        --bcc archive@example.com \
        --subject "Hello there" \
        --body "This is the email body." \
        --attach report.pdf --attach data.csv
"""

import argparse
import mimetypes
import os
import smtplib
import sys
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# Gmail (and most providers) cap total message size around 25MB; leave
# headroom for headers/base64 overhead.
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024


def _split_addresses(value: str):
    if not value:
        return []
    return [addr.strip() for addr in value.split(",") if addr.strip()]


def _normalize_body(body: str) -> str:
    """
    Defensively convert literal escape sequences (e.g. a caller passing the
    two characters backslash+n instead of an actual newline) into real
    newlines. This handles the common case where body text was assembled
    upstream and the '\\n' never got interpreted as a line break, which
    otherwise shows up as literal "\n" in the sent email.
    """
    return body.replace("\\r\\n", "\n").replace("\\n", "\n")


def _attach_file(msg: MIMEMultipart, filepath: str):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Attachment not found: {filepath}")

    filesize = os.path.getsize(filepath)
    if filesize > MAX_ATTACHMENT_BYTES:
        raise ValueError(
            f"Attachment '{filepath}' is {filesize / (1024 * 1024):.1f}MB, "
            f"which exceeds the {MAX_ATTACHMENT_BYTES / (1024 * 1024):.0f}MB limit per file."
        )

    ctype, encoding = mimetypes.guess_type(filepath)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)

    with open(filepath, "rb") as f:
        part = MIMEBase(maintype, subtype)
        part.set_payload(f.read())

    encoders.encode_base64(part)
    filename = os.path.basename(filepath)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)


def send_email(
    to_address: str,
    subject: str,
    body: str,
    sender_email: str,
    sender_password: str,
    cc_address: str = "",
    bcc_address: str = "",
    attachments: Optional[List[str]] = None,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
    is_html: bool = False,
):
    """
    Send an email with a dynamic recipient, subject, body, optional CC/BCC,
    and optional file attachments.

    Args:
        to_address: Recipient email address (or comma-separated list).
        subject: Email subject line.
        body: Email content.
        sender_email: The "from" email address / login username.
        sender_password: Password or app-specific password for the sender account.
        cc_address: CC recipient(s), comma-separated. Visible to all recipients.
        bcc_address: BCC recipient(s), comma-separated. Hidden from all recipients.
        attachments: List of file paths to attach.
        smtp_server: SMTP server host (default: Gmail's).
        smtp_port: SMTP server port (default: 587 for TLS).
        is_html: If True, sends body as HTML instead of plain text.
    """
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_address
    if cc_address:
        msg["Cc"] = cc_address
    # Bcc is intentionally never set as a header - it's only used in the
    # envelope recipient list below, which is what keeps it hidden.
    msg["Subject"] = subject

    content_type = "html" if is_html else "plain"
    msg.attach(MIMEText(_normalize_body(body), content_type))

    for filepath in attachments or []:
        _attach_file(msg, filepath)

    to_list = _split_addresses(to_address)
    cc_list = _split_addresses(cc_address)
    bcc_list = _split_addresses(bcc_address)
    all_recipients = to_list + cc_list + bcc_list

    if not all_recipients:
        raise ValueError("No recipients specified (--to/--cc/--bcc were all empty).")

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, all_recipients, msg.as_string())

    summary = f"Email sent to {to_address}"
    if cc_address:
        summary += f" (cc: {cc_address})"
    if bcc_address:
        summary += f" (bcc: {bcc_address})"
    print(summary)


def parse_args():
    parser = argparse.ArgumentParser(description="Send a dynamic email.")
    parser.add_argument("--to", required=True, help="Recipient email address(es), comma-separated")
    parser.add_argument("--cc", default="", help="CC email address(es), comma-separated")
    parser.add_argument("--bcc", default="", help="BCC email address(es), comma-separated")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--body", required=True, help="Email body content")
    parser.add_argument(
        "--attach",
        action="append",
        default=[],
        metavar="FILEPATH",
        help="Path to a file to attach. Repeat for multiple attachments (e.g. --attach a.pdf --attach b.csv)",
    )
    parser.add_argument("--sender", default=SENDER_EMAIL, help="Sender email (defaults to SENDER_EMAIL in .env)")
    parser.add_argument("--password", default=SENDER_PASSWORD, help="Sender password/app password (defaults to SENDER_PASSWORD in .env)")
    parser.add_argument("--smtp-server", default="smtp.gmail.com", help="SMTP server (default: smtp.gmail.com)")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP port (default: 587)")
    parser.add_argument("--html", action="store_true", help="Send body as HTML")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.sender or not args.password:
        sys.exit(
            "Error: sender email/password not set. Provide --sender/--password "
            "or set SENDER_EMAIL/SENDER_PASSWORD in a .env file."
        )

    try:
        send_email(
            to_address=args.to,
            subject=args.subject,
            body=args.body,
            sender_email=args.sender,
            sender_password=args.password,
            cc_address=args.cc,
            bcc_address=args.bcc,
            attachments=args.attach,
            smtp_server=args.smtp_server,
            smtp_port=args.smtp_port,
            is_html=args.html,
        )
    except (FileNotFoundError, ValueError) as e:
        sys.exit(f"Error: {e}")