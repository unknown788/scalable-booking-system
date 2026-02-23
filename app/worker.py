# app/worker.py
import os
import smtplib
from email.message import EmailMessage
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


def _send_via_sendgrid(msg: EmailMessage):
    """Send using SendGrid's SMTP relay (port 587, STARTTLS)."""
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY is not set")
    with smtplib.SMTP("smtp.sendgrid.net", 587) as s:
        s.ehlo()
        s.starttls()
        s.login("apikey", api_key)   # SendGrid: username is literally "apikey"
        s.send_message(msg)


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
            _send_via_sendgrid(msg)
        else:
            _send_via_mailpit(msg)
        logger.info(f"Confirmation sent for booking_id={booking_id} to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send email for booking_id={booking_id}. Error: {e}")
        # Re-raise so Celery marks task as FAILED and can retry
        raise

    return f"Confirmation for booking {booking_id} processed."
