# 01 — System Overview & Architecture

> Read this first. Everything else builds on this.

---

## What This System Does

A production-deployed, distributed seat-booking platform where:
- **Customers** browse events, view real-time seat availability, and book seats
- **Organizers** create venues and events
- The system **guarantees no two users can book the same seat** — even under simultaneous requests
- A **confirmation email** is sent asynchronously after every booking

Live URLs:
- Frontend: https://frontend-omega-beige-26.vercel.app
- Backend API: https://scalable-booking-app.herokuapp.com
- API Docs (Swagger): https://scalable-booking-app.herokuapp.com/docs

---

## The 7 Services

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                          │
│                     Next.js 15 on Vercel                         │
└────────────────────────────┬────────────────────────────────────┘
                             │  HTTPS REST (JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Web Dyno (Heroku)                      │
│            uvicorn + async workers, pool_size=20                 │
└──────┬──────────────┬──────────────┬──────────────┬─────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
  PostgreSQL       Redis 7      RabbitMQ       (responds to client)
  (NeonDB)      (Upstash)    (CloudAMQP)
  Primary DB    Read cache     Task queue
  ACID txns     TTL 300s      for emails
       │                           │
       │                           ▼
       │                   Celery Worker Dyno (Heroku)
       │                   sends email via Resend API
       │
  (Alembic
  migrations)
```

### Local Development (Docker Compose) adds:
- **test-db** (port 5433) — isolated PostgreSQL for pytest
- **Mailpit** (port 8025) — local SMTP UI to inspect emails without Resend

---

## Request Flow: Booking a Seat

This is the most important flow. Know every step.

```
1. User clicks "Book" on frontend
        ↓
2. POST /api/v1/bookings/
   Authorization: Bearer <JWT>
   Body: { event_id: 5, seat_ids: [42, 43] }
        ↓
3. FastAPI extracts JWT → verifies signature → loads User from DB
        ↓
4. booking_service.create_new_booking() runs:
   a. Verify event exists (SELECT from event)
   b. Verify user exists (SELECT from user)
   c. INSERT INTO booking (user_id) → flush → get booking.id
   d. INSERT INTO ticket (booking_id, event_id, seat_id, price) × N seats
   e. db.commit() ← PostgreSQL enforces UNIQUE(event_id, seat_id) HERE
      → If race: IntegrityError → rollback → HTTP 409
      → If first: commit succeeds
   f. Re-query booking with joinedload (tickets → seat + event → venue)
   g. delete_from_cache("availability:5")   ← invalidate Redis key
   h. send_booking_confirmation.delay(booking_id, user.email) ← to RabbitMQ
        ↓
5. FastAPI returns HTTP 200 with full Booking JSON
        ↓
6. RabbitMQ delivers task to Celery worker (separate Heroku dyno)
        ↓
7. Worker calls Resend API → email delivered to user
```

**Key insight**: Steps 6–7 happen completely outside the HTTP request lifecycle. The user gets their 200 response before the email is sent.

---

## Request Flow: Checking Seat Availability

```
1. GET /api/v1/events/5/availability
        ↓
2. event_service.get_event_availability(db, event_id=5)
        ↓
3. get_from_cache("availability:5")
   ├── CACHE HIT  → return JSON from Redis (~8ms)
   └── CACHE MISS → query PostgreSQL
                    → all seats for venue
                    → booked seat_ids for this event
                    → build availability dict
                    → set_to_cache("availability:5", data, ex=300)
                    → return (~148ms)
```

**Cache invalidation**: whenever a booking commits successfully, `delete_from_cache("availability:{event_id}")` is called immediately. Next request rebuilds from DB.

---

## Tech Stack Choices — The "Why" (crucial for interviews)

| Technology | Why This One |
|---|---|
| **FastAPI** | Native async, auto OpenAPI docs, type-safe with Pydantic, fastest Python web framework by benchmarks |
| **PostgreSQL** | ACID transactions + `UNIQUE` constraints — the database becomes the concurrency arbiter, not app code |
| **SQLAlchemy** | ORM with connection pooling (`pool_size=20, max_overflow=10`) for burst traffic |
| **Alembic** | Version-controlled schema migrations — DB changes are reproducible and reversible |
| **Redis** | In-memory data store for read-through cache; `socket_timeout=2` ensures it fails fast and never blocks the API |
| **Celery** | Distributed task queue; `acks_late=True` means a task is only removed from the queue after it succeeds |
| **RabbitMQ** | Message broker for Celery; chosen over Redis-as-broker because it's a proper message queue with durability guarantees |
| **Next.js 15** | React with App Router, SSR, TypeScript — standard production frontend choice |
| **Docker** | Reproducible builds; the same image runs locally and in production |
| **NeonDB** | Serverless PostgreSQL with connection pooler — needed because Heroku Eco dynos spin down and cold-start connection pools |
| **Upstash Redis** | Serverless Redis (free tier) — no persistent connection required |
| **Heroku** | Container Registry deployment — deploy any Docker image, supports multiple process types (web + worker) |
| **Vercel** | Zero-config Next.js deployment, automatic preview URLs |

---

## Code Structure

```
backend/
├── app/
│   ├── main.py              ← FastAPI app creation, CORS, router registration
│   ├── worker.py            ← Celery task: send_booking_confirmation
│   ├── api/v1/
│   │   ├── api.py           ← Router aggregation (all endpoints registered here)
│   │   └── endpoints/
│   │       ├── auth.py      ← POST /auth/token (login)
│   │       ├── users.py     ← POST /users/signup
│   │       ├── public.py    ← GET /events/, /events/{id}, /events/{id}/availability
│   │       ├── bookings.py  ← GET /bookings/my, POST /bookings/
│   │       ├── events.py    ← POST /organizer/venues/, /organizer/events/
│   │       └── metrics.py   ← GET /metrics
│   ├── core/
│   │   ├── config.py        ← Pydantic settings (reads from env vars / .env file)
│   │   ├── security.py      ← JWT creation/verification, Argon2 password hashing
│   │   └── celery_app.py    ← Celery app instance with RabbitMQ broker
│   ├── db/
│   │   ├── session.py       ← SQLAlchemy engine + SessionLocal (pool_size=20)
│   │   ├── cache.py         ← Redis client with SSL + connection pool
│   │   ├── deps.py          ← FastAPI dependency injection (get_db, get_current_user)
│   │   └── base_class.py    ← Declarative base with auto tablename
│   ├── models/              ← SQLAlchemy ORM models
│   │   ├── user.py          ← User, UserRole
│   │   ├── event.py         ← Event, Venue, Seat, EventType
│   │   └── booking.py       ← Booking, Ticket, BookingStatus
│   ├── schemas/             ← Pydantic request/response schemas
│   ├── crud/                ← Basic DB operations (get, create, list)
│   └── services/            ← Business logic layer
│       ├── booking_service.py
│       ├── event_service.py
│       └── cache_service.py
├── alembic/                 ← DB migration versions
├── tests/
│   ├── conftest.py
│   ├── test_concurrency.py  ← The 50-user race condition proof
│   └── api/v1/test_booking_flow.py
└── docker-compose.yml       ← 7-service local stack
```

---

## Environment Variables (What Goes Where)

| Variable | Used By | What It Is |
|---|---|---|
| `DATABASE_URL` | FastAPI, Alembic | NeonDB PostgreSQL connection string |
| `SECRET_KEY` | FastAPI security.py | JWT signing secret (HS256) |
| `RABBITMQ_URL` | Celery broker | CloudAMQP AMQP URL |
| `REDIS_URL` | Redis client | Upstash Redis URL |
| `RESEND_API_KEY` | worker.py | Resend email API key |
| `RESEND_TO_OVERRIDE` | worker.py | Force all emails to this address (sandbox workaround) |
| `ENVIRONMENT` | cache.py, worker.py | `"production"` enables SSL for Redis, routes to Resend |
| `CORS_ORIGINS` | main.py | Extra comma-separated allowed origins |
| `EMAIL_FROM` | worker.py | From address in emails |
