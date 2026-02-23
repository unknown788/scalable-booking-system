# app/worker.py
import os
import smtplib
from email.message import EmailMessage
from loguru import logger
from app.core.celery_app import celery_app

# ---------------------------------------------------------------------------
# Email helpers
# ---------------------------------------------------------------------------
# Production  → Resend HTTP API (resend.com, free 3000/month, instant signup)
# Development → Local Mailpit container (smtp://mailpit:1025)
# ---------------------------------------------------------------------------

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")


def _send_via_resend(booking_id: int, user_email: str):
    """Send via Resend HTTP API — no SMTP, just one POST request."""
    import urllib.request
    import json

    api_key   = os.environ.get("RESEND_API_KEY", "")
    from_addr = os.environ.get("EMAIL_FROM", "Booking System <onboarding@resend.dev>")

    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    payload = json.dumps({
        "from":    from_addr,
        "to":      [user_email],
        "subject": f"Booking Confirmation: #{booking_id}",
        "text": (
            f"Hello!\n\n"
            f"Thank you for your booking on the Scalable Booking System.\n"
            f"Your Booking ID is: #{booking_id}\n\n"
            f"We look forward to seeing you!\n\n"
            f"— The Booking Team"
        ),
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode()
        logger.info(f"Resend response for booking_id={booking_id}: {body}")


def _send_via_mailpit(booking_id: int, user_email: str):
    """Send using local Mailpit container (dev only)."""
    msg = EmailMessage()
    msg.set_content(
        f"Hello!\n\n"
        f"Thank you for your booking.\n"
        f"Your Booking ID is: #{booking_id}\n\n"
        f"We look forward to seeing you!\n\n"
        f"— The Booking Team"
    )
    msg["Subject"] = f"Booking Confirmation: #{booking_id}"
    msg["From"]    = "booking-system@example.com"
    msg["To"]      = user_email
    with smtplib.SMTP("mailpit", 1025) as s:
        s.send_message(msg)


@celery_app.task(acks_late=True)
def send_booking_confirmation(booking_id: int, user_email: str):
    """
    Celery task: sends a booking confirmation email.
    Routes to Resend API (production) or Mailpit (development).
    """
    try:
        if ENVIRONMENT == "production":
            _send_via_resend(booking_id, user_email)
        else:
            _send_via_mailpit(booking_id, user_email)
        logger.info(f"Confirmation sent for booking_id={booking_id} to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send email for booking_id={booking_id}. Error: {e}")
        raise  # Let Celery mark task FAILED so it can be retried

    return f"Confirmation for booking {booking_id} processed."
