# 06 — Async Pipeline: Celery + RabbitMQ

---

## Why a message queue for emails?

When a user books seats, they expect a fast response — ideally under 100 ms. Sending an email via Resend API takes 200–800 ms and can fail/timeout. If you call the email API synchronously in the booking endpoint:
- The user waits for email delivery before getting their booking confirmation
- If the email API is down, the booking endpoint returns a 500
- Retries would block the web process

The solution: **publish a message to a queue and return immediately**. A separate worker process consumes the message and handles the email, completely decoupled from the HTTP request.

---

## The architecture

```
Web Dyno (FastAPI)                RabbitMQ (CloudAMQP)        Worker Dyno (Celery)
─────────────────                 ────────────────────        ────────────────────
POST /bookings/
  db.commit() ✓
  .delay(booking_id, email)  →→→  [message queue]  →→→  send_booking_confirmation()
  return Booking JSON                                       resend.Emails.send(...)
  (< 50 ms)                                                logger.info("sent")
```

The web dyno and worker dyno are **separate Heroku dynos** running separate Docker images. They communicate only through RabbitMQ.

---

## Celery configuration

```python
# app/core/celery_app.py
celery_app = Celery(
    "worker",
    broker=os.environ.get("RABBITMQ_URL"),
    backend=None,   # ← fire-and-forget, no result storage
)

celery_app.conf.update(
    task_ignore_result=True,
    task_store_errors_even_if_ignored=False,
    broker_connection_retry_on_startup=True,
)
```

**`backend=None`** is critical. When a result backend is set (e.g. Redis), Celery opens a Redis pub/sub connection on every `.delay()` call to wait for the result. Since this is fire-and-forget (we don't need the result), setting `backend=None` eliminates that connection entirely. This was a real production bug — booking POSTs were returning 500s until this was fixed.

---

## The Celery task

```python
# app/worker.py
@celery_app.task(acks_late=True, ignore_result=True)
def send_booking_confirmation(booking_id: int, user_email: str) -> None:
    try:
        if ENVIRONMENT == "production":
            _send_via_resend(booking_id, user_email)
        else:
            _send_via_mailpit(booking_id, user_email)
        logger.info(f"Confirmation sent  booking_id={booking_id}  to={user_email}")
    except Exception as exc:
        logger.error(f"Email failed  booking_id={booking_id}  error={exc}")
        raise  # re-raise → Celery marks task FAILED, will retry
```

### `acks_late=True` — why this matters

By default, RabbitMQ **acknowledges** (removes) a message from the queue as soon as the worker **receives** it, before processing. If the worker process dies mid-processing (crash, OOM kill, dyno restart), the message is lost.

With `acks_late=True`, the message is only acknowledged **after the task function returns successfully**. If the worker dies, RabbitMQ requeues the message and another worker picks it up.

This gives **at-least-once delivery** — the email will be sent even if the worker crashes.

---

## How `.delay()` works

```python
# In booking_service.py
send_booking_confirmation.delay(db_booking.id, user.email)
```

`.delay()` is shorthand for `.apply_async()`. It serialises the arguments (booking_id, email) as JSON, publishes them as a message to RabbitMQ's default `celery` queue, and returns immediately. The web dyno does not wait.

---

## Email routing (Resend sandbox workaround)

Resend's free tier without a verified domain only allows sending to the account owner's email. To work around this in production without a verified domain:

```python
def _send_via_resend(booking_id, user_email):
    to_address = os.environ.get("RESEND_TO_OVERRIDE") or user_email
    # ...
    params = {
        "from": os.environ.get("EMAIL_FROM", "onboarding@resend.dev"),
        "to": [to_address],
        "subject": f"Booking Confirmation: #{booking_id}",
        "text": f"...\nBooked by: {user_email}\n...",
    }
    resend.Emails.send(params)
```

`RESEND_TO_OVERRIDE` is set to the account owner's Gmail in Heroku config. The email body still includes the real user's email address. To enable real user emails, verify a domain in Resend and remove the config var.

---

## Dev environment: Mailpit

Locally, emails are sent to **Mailpit** — a local SMTP server that captures emails and provides a web UI at `http://localhost:8025`. No real emails are sent in development.

```python
def _send_via_mailpit(booking_id, user_email):
    msg = EmailMessage()
    msg["Subject"] = f"Booking Confirmation: #{booking_id}"
    msg["From"] = os.environ.get("EMAIL_FROM")
    msg["To"] = user_email
    with smtplib.SMTP("mailpit", 1025) as s:
        s.send_message(msg)
```

Mailpit is a Docker service in `docker-compose.yml` — port 8025 for the web UI, 1025 for SMTP.

---

## Starting the worker locally

```bash
celery -A app.worker worker --loglevel=info
```

The `-A app.worker` tells Celery to find the `celery_app` instance in `app/worker.py` (actually in `app/core/celery_app.py`, imported by `worker.py`).

On Heroku, the worker Dockerfile runs this as the CMD:
```dockerfile
CMD ["celery", "-A", "app.worker", "worker", "--loglevel=info"]
```

---

## RabbitMQ vs Redis as broker — why RabbitMQ?

| | RabbitMQ | Redis as broker |
|---|---|---|
| Designed for | Message queuing | Key-value cache |
| Persistence | Messages persisted to disk | Messages in memory (can lose on restart) |
| `acks_late` reliability | Rock solid | Weaker guarantees |
| Production readiness | Industry standard for task queues | OK for simple cases |

RabbitMQ's AMQP protocol was built for exactly this use case. CloudAMQP provides a free tier suitable for this project.

---

## Interview one-liner

> "I decouple email confirmation from the HTTP request using Celery with RabbitMQ as the broker. The booking endpoint publishes a message and returns immediately — keeping API latency under 50 ms regardless of email delivery time. I use `acks_late=True` so the message is only acknowledged after successful delivery, giving at-least-once semantics. The result backend is set to None because this is fire-and-forget — that also fixed a production bug where Celery was opening a Redis pub/sub connection on every `.delay()` call and causing 500s on the web dyno."
