# Scalable Booking System

[![Live Demo](https://img.shields.io/badge/Live_Demo-booking.404by.me-blueviolet?style=for-the-badge&logo=vercel)](https://booking.404by.me/)
[![API Docs](https://img.shields.io/badge/API_Docs-%2Fdocs-green?style=for-the-badge&logo=fastapi)](https://booking.404by.me/docs)
[![CI](https://github.com/unknown788/scalable-booking-system/actions/workflows/main.yml/badge.svg)](https://github.com/unknown788/scalable-booking-system/actions)

> A production-grade distributed ticket-booking platform engineered for **concurrency safety**, **measurable performance**, and **SDE-2-level system design depth**.

---

## Key Numbers (Measured, Not Estimated)

| Metric | Value | How |
|--------|-------|-----|
| Cache speedup | **16.6×** | avg 1.6 ms (Redis) vs 26.6 ms (DB) |
| Cache hit rate | **62.5%** | 295 / 472 requests served from cache |
| Peak throughput | **37 RPS** | Locust 80 concurrent users, 60 s |
| Error rate under load | **< 1%** | same Locust run |
| Concurrency correctness | **1 / 50** | 50 simultaneous requests → exactly 1 booking, 49 × HTTP 409 |
| DB connection pool | **pool=20, overflow=10** | zero timeout errors under load |

> Full methodology, raw data, and charts → [`proof/analysis.ipynb`](proof/analysis.ipynb)
> Architecture diagrams, LLD, HLD → [`proof/architecture.ipynb`](proof/architecture.ipynb)

---

## Architecture

Seven Docker services, each with a single responsibility:

```
Browser ──HTTPS──► Next.js (3000)
                       │ REST/JSON
                       ▼
              FastAPI + Uvicorn (8000)
              /api/v1  ·  JWT Auth  ·  Pydantic v2
               │              │              │
        SQLAlchemy        Redis DEL      Celery .delay()
        pool=20           on write       (fire & forget)
               │              │              │
        PostgreSQL 15    Redis 7 TTL=300s  RabbitMQ ──► Celery Worker ──SMTP──► Mailpit
        UniqueConstraint  cache_hits/ms    AMQP            acks_late=True
```

| Service | Port | Role |
|---------|------|------|
| `backend` | 8000 | FastAPI + Uvicorn — all API logic |
| `db` | 5434 → 5432 | PostgreSQL 15 — primary data store |
| `test_db` | 5433 → 5432 | PostgreSQL 15 — isolated test database |
| `redis` | 6380 → 6379 | Redis 7 — availability cache + metrics counters |
| `rabbitmq` | 5672, 15672 | RabbitMQ 3.13 — async task queue (AMQP) |
| `mailpit` | 8025, 1025 | Dev SMTP server — email confirmation testing |
| `notification_worker` | — | Celery 5.4 — consumes booking-confirmation tasks |

---

## How Concurrency Is Solved

The core problem: 50 users simultaneously trying to book the last seat.

**Solution: PostgreSQL `UniqueConstraint` as the atomic lock**

```python
# models/booking.py
class Ticket(Base):
    __table_args__ = (
        UniqueConstraint("event_id", "seat_id", name="_event_seat_uc"),
    )
```

```python
# services/booking_service.py
try:
    db.add(db_booking)
    db.flush()                          # get booking.id
    for seat_id in booking_in.seat_ids:
        db.add(Ticket(event_id=..., seat_id=seat_id, ...))
    db.commit()                         # ← PostgreSQL enforces UC here
    cache_service.delete_from_cache(f"availability:{event_id}")
    send_booking_confirmation.delay(booking_id, email)
    return db_booking
except IntegrityError:
    db.rollback()
    raise HTTPException(409, "Seat already booked")
```

**Why this over alternatives:**

| Approach | Why not chosen |
|----------|----------------|
| Redis `SETNX` pre-lock | TTL expiry can leak locks; needs extra round-trip |
| Pessimistic `SELECT FOR UPDATE` | Serialises all reads; kills read throughput |
| Application-level mutex | Breaks with multiple API replicas |
| **DB `UniqueConstraint`** ✅ | Atomic, replica-safe, zero extra infra, 100% reliable |

**Test proof** (`tests/test_concurrency.py`):

```
50 users · asyncio.gather · 1 seat
→ HTTP 200: 1   HTTP 409: 49   Unexpected: 0   ✅
```

---

## Redis Caching

Pattern: **cache-aside with event-driven invalidation**.

```python
# GET /api/v1/events/{id}/availability
cached = get_from_cache(f"availability:{event_id}")   # ~1.6 ms
if cached:
    return cached                                       # cache HIT

data = db.query(...)                                   # ~26.6 ms — cache MISS
set_to_cache(f"availability:{event_id}", data, ttl=300)
return data
```

On any booking commit → `DEL availability:{event_id}` — next read is always fresh.

Live metrics from `GET /api/v1/metrics`:
```json
{
  "cache_hits": 295,  "cache_misses": 177,
  "hit_rate_pct": 62.5,
  "avg_cache_ms": 1.6,  "avg_db_ms": 26.55,
  "speedup_interpretation": "Cache is 16.6x faster than DB"
}
```

---

## Async Notifications

Email confirmation is **off the critical path** — zero ms added to the booking response.

```
FastAPI  ──AMQP .delay()──►  RabbitMQ  ──consume──►  Celery Worker
                                                          │
                                                     smtplib → Mailpit
                                                     acks_late=True
```

`acks_late=True` — if the worker crashes mid-send, RabbitMQ requeues the task (at-least-once delivery). Synchronous email would add 200–500 ms to every booking p99.

---

## Tech Stack

**Backend:** FastAPI 0.116 · Uvicorn · SQLAlchemy 2.0 · Alembic · PostgreSQL 15 · Redis 7 · Celery 5.4 · RabbitMQ 3.13 · Pydantic v2 · JWT/Argon2 · Loguru

**Frontend:** Next.js 15 (App Router) · TypeScript · Tailwind CSS · dark luxury theme

**Testing:** pytest 8.3 · pytest-asyncio · httpx · Locust 2.32

**Infrastructure:** Docker Compose (7 services) · GitHub Actions CI · Heroku (backend) · Vercel (frontend) · Neon (PostgreSQL) · Upstash (Redis) · CloudAMQP (RabbitMQ)

---

## Proof & Diagrams

All visual proof lives in [`proof/`](proof/):

| File | Description |
|------|-------------|
| [`analysis.ipynb`](proof/analysis.ipynb) | 4-panel performance dashboard + concurrency bar chart |
| [`architecture.ipynb`](proof/architecture.ipynb) | System architecture · LLD · ERD · swimlane · scaling roadmap |
| [`performance_dashboard.png`](proof/performance_dashboard.png) | Cache pie · latency bars · RPS timeline · percentile chart |
| [`architecture_diagram.png`](proof/architecture_diagram.png) | All 7 services with ports and data-flow arrows |
| [`lld_class_diagram.png`](proof/lld_class_diagram.png) | UML class diagram — attributes, methods, visibility, relationships |
| [`erd_diagram.png`](proof/erd_diagram.png) | Entity-relationship diagram — 6 DB models + UniqueConstraint |
| [`request_flow_swimlane.png`](proof/request_flow_swimlane.png) | `POST /bookings` traced through every layer (happy + conflict path) |
| [`design_decisions.png`](proof/design_decisions.png) | 5 architectural decisions with trade-off analysis |
| [`concurrency_mechanism.png`](proof/concurrency_mechanism.png) | Race-condition timeline + live metric cards |
| [`scaling_roadmap.png`](proof/scaling_roadmap.png) | Current → Production → Hyperscale evolution |
| [`load_test_report.html`](proof/load_test_report.html) | Full Locust HTML report (80 users, 60 s) |
| [`concurrency_test_output.txt`](proof/concurrency_test_output.txt) | Raw pytest output — `1 passed in 16.xx s` |

---

## Running Locally

```bash
# 1. Clone
git clone https://github.com/unknown788/scalable-booking-system
cd scalable-booking-system/backend

# 2. Start all 7 services
docker compose up -d --build

# 3. Apply DB migrations
docker compose exec backend alembic upgrade head

# 4. Run concurrency test
docker compose exec backend pytest tests/test_concurrency.py -v

# 5. Check live metrics
curl http://localhost:8000/api/v1/metrics | python3 -m json.tool
```

| URL | What |
|-----|------|
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:3000` | Frontend (`cd ../frontend && npm run dev`) |
| `http://localhost:15672` | RabbitMQ management UI (guest / guest) |
| `http://localhost:8025` | Mailpit — captured confirmation emails |

---

## Scaling Roadmap

```
Current (Docker Compose, ~100 users)
  → Add Nginx LB + N FastAPI replicas   (~1k users — UC already replica-safe)
  → PgBouncer + RDS Multi-AZ            (~10k users)
  -> ElastiCache Redis cluster           (~10k users)
  -> Redis SETNX pre-reservation         (reduce DB writes on conflicts)
  -> CQRS — separate read replicas       (~100k users)
  -> Kafka for event streaming           (hyperscale async)
```
