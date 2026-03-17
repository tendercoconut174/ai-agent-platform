"""Email sender tool – send emails via SMTP."""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


def _is_email_configured() -> bool:
    """Check if SMTP is configured."""
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    return bool(host and user and password)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_email: str | None = None,
) -> dict[str, Any]:
    """Send an email via SMTP.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Email body (plain text).
        from_email: Sender email (defaults to SMTP_FROM or SMTP_USER).

    Returns:
        Dict with success, message, and optional error.
    """
    if not _is_email_configured():
        return {
            "success": False,
            "message": "Email not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env",
            "error": "SMTP_NOT_CONFIGURED",
        }

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = from_email or os.getenv("SMTP_FROM") or user

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(sender, to_email, msg.as_string())
        logger.info("[email_sender] Email sent | to=%s | subject=%s", to_email, subject[:50])
        return {"success": True, "message": f"Email sent to {to_email}"}
    except smtplib.SMTPAuthenticationError as e:
        logger.warning("[email_sender] SMTP auth failed: %s", e)
        return {
            "success": False,
            "message": "SMTP authentication failed. For Gmail, use an App Password.",
            "error": str(e),
        }
    except Exception as e:
        logger.exception("[email_sender] Email send failed: %s", e)
        return {"success": False, "message": str(e), "error": str(e)}
