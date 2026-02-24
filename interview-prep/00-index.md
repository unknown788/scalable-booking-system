# Interview Prep — Index

Study these in order before an interview. Each doc is self-contained.

---

| # | File | What it covers | Priority |
|---|------|----------------|----------|
| 01 | `01-system-overview-and-architecture.md` | Big picture, components, why each exists | Read first |
| 02 | `02-database-and-data-model.md` | Schema, constraints, relationships, migrations | High |
| 03 | `03-backend-deep-dive.md` | Every endpoint, auth/JWT flow, services vs CRUD, DI | High |
| 04 | `04-concurrency-and-core-problem.md` | **The most important doc.** Double-booking, why naive fails, UniqueConstraint proof | MUST KNOW |
| 05 | `05-caching-and-performance.md` | Redis read-through, TTL, invalidation, metrics endpoint, load test numbers | High |
| 06 | `06-async-pipeline.md` | Celery, RabbitMQ, acks_late, backend=None, email routing | Medium |
| 07 | `07-deployment-and-infrastructure.md` | Docker, docker-compose, Heroku container registry, NeonDB, Upstash, Vercel | Medium |
| 08 | `08-interview-qa.md` | 31 Q&As with model answers specific to this project | Read last — test yourself |

---

## The 5 things you MUST be able to say cold

1. **The concurrency solution**: `UNIQUE(event_id, seat_id)` on the tickets table. First write wins, second gets IntegrityError → 409. Proved with 50-concurrent-user test: exactly 0 double-bookings.

2. **The cache numbers**: Redis read-through on `/availability`. 8.9 ms cached vs 148 ms DB. 16.6× speedup. 62.5% hit rate at 37 RPS peak.

3. **Why backend=None on Celery**: Fire-and-forget tasks don't need result storage. With a Redis backend, every `.delay()` opened a pub/sub connection → was causing 500s in production. Removing it fixed it.

4. **Why not Redis distributed lock for concurrency**: Not atomic with PostgreSQL, requires TTL tuning, breaks if Redis is down, doesn't work across dynos reliably. DB constraint is simpler, atomic, and doesn't add infrastructure.

5. **The full booking request flow**: JWT auth → service layer → db.flush() → INSERT tickets → db.commit() (constraint enforced) → cache invalidate → `.delay()` to RabbitMQ → return JSON. Worker picks up message → calls Resend API → email sent.

---

## Production URLs

- Frontend: https://frontend-omega-beige-26.vercel.app
- API: https://scalable-booking-app.herokuapp.com
- API docs: https://scalable-booking-app.herokuapp.com/docs
- Metrics: https://scalable-booking-app.herokuapp.com/api/v1/metrics
