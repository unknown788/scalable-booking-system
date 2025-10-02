# app/worker.py
import smtplib
from email.message import EmailMessage
from app.core.celery_app import celery_app


@celery_app.task(acks_late=True)
def send_booking_confirmation(booking_id: int, user_email: str):
    """
    Connects to the local Mailpit server and sends a fake confirmation email.
    """
    msg = EmailMessage()
    msg.set_content(
        f"Hello!\n\nThank you for your booking.\nYour booking ID is: {booking_id}\n\nWe look forward to seeing you!")
    msg["Subject"] = f"Booking Confirmation: #{booking_id}"
    msg["From"] = "booking-system@example.com"
    msg["To"] = user_email

    try:
        # Connect to the Mailpit Docker container on its SMTP port
        with smtplib.SMTP("mailpit", 1025) as s:
            s.send_message(msg)
        print(
            f"Successfully sent confirmation for booking_id: {booking_id} to {user_email}")
    except Exception as e:
        print(f"Failed to send email for booking_id: {booking_id}. Error: {e}")

    return f"Confirmation for booking {booking_id} processed."
