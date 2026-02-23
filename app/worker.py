# app/worker.py
import os
import smtplib
from email.message import EmailMessage
from loguru import logger
from app.core.celery_app import celery_app

# ---------------------------------------------------------------------------
# Email helpers — Resend API in production, Mailpit in development
# ---------------------------------------------------------------------------

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")


def _send_via_resend(booking_id: int, user_email: str) -> None:
    """Send via Resend API (resend SDK v2.x, Python >= 3.10)."""
    import resend  # lazy import so missing SDK doesn't crash dev

    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    resend.api_key = api_key
    params: resend.Emails.SendParams = {
        "from": os.environ.get("EMAIL_FROM", "onboarding@resend.dev"),
        "to": [user_email],
        "subject": f"Booking Confirmation: #{booking_id}",
        "text": (
            "Hello!\n\n"
            "Thank you for your booking on the Scalable Booking System.\n"
            f"Your Booking ID is: #{booking_id}\n\n"
            "We look forward to seeing you!\n\n"
            "— The Booking Team"
        ),
    }
    resend.Emails.send(params)


def _send_via_mailpit(booking_id: int, user_email: str) -> None:
    """Send via local Mailpit SMTP container (dev / docker-compose only)."""
    msg = EmailMessage()
    msg.set_content(
        "Hello!\n\n"
        "Thank you for your booking on the Scalable Booking System.\n"
        f"Your Booking ID is: #{booking_id}\n\n"
        "We look forward to seeing you!\n\n"
        "— The Booking Team"
    )
    msg["Subject"] = f"Booking Confirmation: #{booking_id}"
    msg["From"]    = os.environ.get("EMAIL_FROM", "booking-system@example.com")
    msg["To"]      = user_email
    with smtplib.SMTP("mailpit", 1025) as s:
        s.send_message(msg)


@celery_app.task(acks_late=True, ignore_result=True)
def send_booking_confirmation(booking_id: int, user_email: str) -> None:
    """
    Celery task: sends a booking confirmation email.
    Routes to Resend API (ENVIRONMENT=production) or Mailpit (development).
    acks_late=True: message only acknowledged after success; requeued on crash.
    """
    try:
        if ENVIRONMENT == "production":
            _send_via_resend(booking_id, user_email)
        else:
            _send_via_mailpit(booking_id, user_email)
        logger.info(f"Confirmation sent  booking_id={booking_id}  to={user_email}")
    except Exception as exc:
        logger.error(f"Email failed  booking_id={booking_id}  error={exc}")
        raise  # re-raise → Celery marks task FAILED; retries via broker
