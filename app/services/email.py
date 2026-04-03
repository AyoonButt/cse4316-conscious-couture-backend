"""
Email notification service using Python's built-in smtplib.
Requires SMTP_HOST, SMTP_USER, SMTP_PASSWORD and EMAIL_ENABLED=True in .env.
All sends are fire-and-forget: exceptions are logged, never raised.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..config import settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, body_html: str) -> None:
    """Internal send — silently skips if email is disabled or misconfigured."""
    if not settings.EMAIL_ENABLED or not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.debug("Email skipped (EMAIL_ENABLED=False or SMTP not configured): %s", subject)
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())

        logger.info("Email sent (%s) → %s", subject, to_email)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)


# ── Public helpers ────────────────────────────────────────────────────────

def send_swap_request_email(to_email: str, requester_name: str, item_name: str) -> None:
    """Notify the item owner that someone wants to swap with them."""
    subject = "You have a new swap request — Conscious Couture"
    body = f"""
    <p>Hi,</p>
    <p><strong>{requester_name}</strong> has requested to swap for your item <strong>{item_name}</strong>.</p>
    <p>Log in to your dashboard to accept or decline the request.</p>
    <br>
    <p>— The Conscious Couture Team</p>
    """
    _send(to_email, subject, body)


def send_swap_accepted_email(to_email: str, owner_name: str, item_name: str) -> None:
    """Notify the requester that their swap was accepted."""
    subject = "Your swap request was accepted! — Conscious Couture"
    body = f"""
    <p>Great news!</p>
    <p><strong>{owner_name}</strong> accepted your swap request for <strong>{item_name}</strong>.</p>
    <p>The items have been exchanged. Check your dashboard for details.</p>
    <br>
    <p>— The Conscious Couture Team</p>
    """
    _send(to_email, subject, body)


def send_swap_declined_email(to_email: str, item_name: str) -> None:
    """Notify the requester that their swap was declined."""
    subject = "Your swap request was declined — Conscious Couture"
    body = f"""
    <p>Unfortunately, your swap request for <strong>{item_name}</strong> was declined.</p>
    <p>Don't worry — there are plenty of other items to explore!</p>
    <br>
    <p>— The Conscious Couture Team</p>
    """
    _send(to_email, subject, body)


def send_swap_cancelled_email(to_email: str, requester_name: str, item_name: str) -> None:
    """Notify the item owner (User B) that the swap request was cancelled by the requester."""
    subject = "A swap request was cancelled — Conscious Couture"
    body = f"""
    <p>Hi,</p>
    <p><strong>{requester_name}</strong> has cancelled their swap request for your item <strong>{item_name}</strong>.</p>
    <p>Your item is still listed and available for other swap requests.</p>
    <br>
    <p>— The Conscious Couture Team</p>
    """
    _send(to_email, subject, body)
