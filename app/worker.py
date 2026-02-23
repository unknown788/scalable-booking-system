# app/worker.py
import os
import smtplib
from email.message import EmailMessage
try:
    from resend import Resend
except Exception:
    Resend = None
from loguru import logger
from app.core.celery_app import celery_app

# ---------------------------------------------------------------------------
# Email helpers
# ---------------------------------------------------------------------------
# In production (ENVIRONMENT=production) we send via SendGrid's SMTP relay.
# In development we send via local Mailpit container.
# ---------------------------------------------------------------------------

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

def _build_message(booking_id: int, user_email: str) -> EmailMessage:
    msg = EmailMessage()
    msg.set_content(
        f"Hello!\n\n"
        f"Thank you for your booking on the Scalable Booking System.\n"
        f"Your Booking ID is: #{booking_id}\n\n"
        f"We look forward to seeing you!\n\n"
        f"— The Booking Team"
    )
    msg["Subject"] = f"Booking Confirmation: #{booking_id}"
    msg["From"]    = os.environ.get("EMAIL_FROM", "booking-system@example.com")
    msg["To"]      = user_email
    return msg


def _send_via_resend(msg: EmailMessage):
    """Send using Resend API via the `resend` Python SDK.
    Falls back to HTTP if SDK missing.
    """
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    # Use resend SDK when available
    if Resend is not None:
        client = Resend(api_key)
        # resend expects html or text; we'll send plain text
        body = msg.get_content()
        client.emails.send(
            from_=msg.get("From"),
            to=[msg.get("To")],
            subject=msg.get("Subject"),
            text=body,
        )
        return

    # Fallback: call Resend HTTP API directly (requests not required here,
    # but we can use the standard library if needed). We'll use httpx if present.
    try:
        import httpx
    except Exception:
        httpx = None

    if httpx is None:
        raise RuntimeError("Resend SDK and httpx are not installed; cannot send email")

    body = msg.get_content()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "from": msg.get("From"),
        "to": [msg.get("To")],
        "subject": msg.get("Subject"),
        "text": body,
    }
    r = httpx.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10.0)
    r.raise_for_status()


def _send_via_mailpit(msg: EmailMessage):
    """Send using local Mailpit container (dev only)."""
    with smtplib.SMTP("mailpit", 1025) as s:
        s.send_message(msg)


@celery_app.task(acks_late=True)
def send_booking_confirmation(booking_id: int, user_email: str):
    """
    Celery task: sends a booking confirmation email.
    Routes to SendGrid (production) or Mailpit (development).
    """
    msg = _build_message(booking_id, user_email)
    try:
        if ENVIRONMENT == "production":
            _send_via_resend(msg)
        else:
            _send_via_mailpit(msg)
        logger.info(f"Confirmation sent for booking_id={booking_id} to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send email for booking_id={booking_id}. Error: {e}")
        # Re-raise so Celery marks task as FAILED and can retry
        raise

    return f"Confirmation for booking {booking_id} processed."
