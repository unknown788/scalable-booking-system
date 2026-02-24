# 08 — Interview Q&A

These are real questions you will be asked. Every answer is specific to this project.

---

## Section A: The Core Problem (most likely to be asked first)

**Q1: Walk me through your project.**

> I built a production-grade seat booking system that solves the double-booking problem under high concurrency. The backend is FastAPI with PostgreSQL, with a Redis cache in front of read-heavy endpoints. I use Celery with RabbitMQ to send booking confirmations asynchronously. The frontend is Next.js 15. Everything is containerised with Docker and deployed — web and worker as separate Heroku dynos, frontend on Vercel, database on NeonDB serverless. The interesting engineering is the concurrency guarantee: I proved it with a test that fires 50 simultaneous booking requests at a single seat and asserts exactly 1 succeeds.

---

**Q2: What is the double-booking problem and how did you solve it?**

> Double-booking happens when two users request the same seat at the same millisecond. A naive "read then write" approach has a race condition — both reads see the seat as available, both writes succeed, the seat is sold twice. I solved it at the database layer using a composite `UNIQUE(event_id, seat_id)` constraint on the tickets table. PostgreSQL enforces this atomically inside the transaction — the first writer wins, the second gets an IntegrityError which I surface as HTTP 409. No application-level locks needed, no Redis distributed locks, no serialisation bottleneck. It's horizontally scalable because the constraint only conflicts when two requests hit the exact same seat.

---

**Q3: Why not use a Redis distributed lock?**

> Redis locks are brittle. If the lock-holder process dies after the booking is committed but before the lock is deleted, the seat stays locked until TTL. Redis and PostgreSQL are two separate systems with no shared transaction — there's no atomicity between them. A PostgreSQL `UNIQUE` constraint is atomic by definition, works even if Redis is down, and doesn't require a separate round-trip. The database is already the source of truth; making it also the concurrency arbiter is the right architecture.

---

**Q4: What's the ACID property your solution relies on?**

> Atomicity and Isolation. Atomicity means if any ticket insert in the transaction fails, all of them roll back — no partial bookings. Isolation at PostgreSQL's default `READ COMMITTED` level means the constraint check at `COMMIT` time sees the fully committed state of the table — if seat 101 was just committed by another transaction, this transaction's constraint check will catch it.

---

**Q5: What if two users book different seats at the same time?**

> They don't conflict at all. The `UNIQUE` constraint is per `(event_id, seat_id)` pair. Two transactions inserting different `seat_id` values have no row-level conflict and both commit successfully. This is the key advantage over `SELECT FOR UPDATE` which would serialize both through a table-level lock.

---

**Q6: How did you prove the concurrency guarantee?**

> I wrote `test_concurrent_booking_only_one_succeeds` in `tests/test_concurrency.py`. It creates a venue with exactly 1 seat, then fires 50 simultaneous HTTP requests — all trying to book that same seat — using `asyncio.gather`. I assert exactly 1 HTTP 200, exactly 49 HTTP 409s, and exactly 1 ticket row in the database. The test uses real `COMMIT`s to a test database — not the standard rollback fixture — because the constraint race only plays out across genuine committed transactions.

---

## Section B: Caching

**Q7: Why did you add caching and where?**

> The most-hit endpoint is `GET /events/{id}/availability` — every user loads it before booking and it gets hammered under load. Without cache each request does two DB queries, a set-difference computation, and JSON serialisation — about 148 ms. I put a Redis read-through cache in front with a 5-minute TTL. The cache is explicitly invalidated on every booking commit, so it's always fresh. Under Locust load test at 80 concurrent users I measured 8.9 ms vs 148 ms — 16.6× speedup.

---

**Q8: How do you keep the cache consistent with the database?**

> Write-invalidate pattern. The cache stores availability data. When a booking is committed to the database, I immediately delete the cache key: `cache_service.delete_from_cache(f"availability:{event_id}")`. The next request sees a miss and rebuilds from the DB. The 5-minute TTL is a safety net for edge cases (e.g. Redis delete fails), not the primary freshness mechanism.

---

**Q9: What happens if Redis goes down?**

> All cache operations are wrapped in try/except. On any Redis error, `get_from_cache` returns `None` (treated as a miss), and `set_to_cache` silently skips. The app falls back to the database transparently — no 500 errors, just slower responses. The cache is an optimisation, not a hard dependency.

---

**Q10: How do you measure whether the cache is working?**

> I built a `/api/v1/metrics` endpoint that returns live stats. Every cache hit/miss increments a Redis counter atomically with `INCR`. Latencies are accumulated with `INCRBYFLOAT`. The metrics endpoint reads these counters and computes hit rate percentage, average cache latency vs average DB latency, and the speedup ratio. After a Locust load test the output showed 62.5% hit rate, 8.9 ms cache vs 148 ms DB, 16.6× speedup.

---

**Q11: Why store metrics in Redis counters instead of a database?**

> Latency. Incrementing a Redis counter on every request adds ~0.5 ms. A database INSERT would add 20–50 ms and create write contention. Redis `INCR` is also atomic — no race condition when multiple workers increment simultaneously. It's the right tool for high-frequency counters.

---

## Section C: Async Pipeline

**Q12: Why use a message queue for emails instead of just calling the API?**

> Email delivery is slow (200–800 ms) and unreliable (can fail, time out, need retries). If I called the Resend API synchronously in the booking endpoint, the user waits for email delivery before getting their booking confirmation. If Resend is down, the booking fails. A message queue decouples these concerns — the booking endpoint publishes a message and returns in under 50 ms. The worker handles delivery independently and retries on failure.

---

**Q13: What is `acks_late=True` and why do you use it?**

> By default, RabbitMQ acknowledges (removes) a message from the queue when the worker *receives* it, before processing. If the worker process dies mid-processing, the message is lost. With `acks_late=True` the message is only acknowledged after the task function returns successfully. If the worker dies, RabbitMQ requeues the message and another worker picks it up. This gives at-least-once delivery guarantee — the email will be sent even if the worker crashes.

---

**Q14: Why no result backend for Celery?**

> The email task is fire-and-forget — I don't need to know the result. Setting `backend=None` means Celery doesn't store task results anywhere. More importantly, when a result backend (like Redis) is configured, Celery opens a Redis pub/sub connection on every `.delay()` call to wait for the result. This was causing a real production bug — every booking POST was opening a Redis pub/sub connection and failing with a 500 because of how Upstash handles pub/sub. Removing the backend fixed it completely.

---

**Q15: RabbitMQ vs Redis as Celery broker — why RabbitMQ?**

> RabbitMQ was designed for message queuing. It persists messages to disk, has robust `acks_late` support, and implements AMQP properly. Redis as a Celery broker keeps messages in memory by default — if Redis restarts, queued tasks are lost. For reliability in a production email pipeline, RabbitMQ is the right choice.

---

## Section D: System Design & Architecture

**Q16: Walk me through the request lifecycle for creating a booking.**

> 1. Client sends POST /api/v1/bookings/ with JWT + body `{event_id, seat_ids}`. 2. FastAPI's `get_current_user` dependency decodes the JWT, validates it, and loads the User from DB. 3. `booking_service.create_new_booking` is called: creates a Booking row, flushes to get the ID, inserts Ticket rows for each seat, commits. PostgreSQL enforces `UNIQUE(event_id, seat_id)` — IntegrityError → 409 if any seat is taken. 4. Cache for this event is invalidated. 5. `.delay(booking_id, user.email)` publishes a message to RabbitMQ — web dyno returns immediately. 6. Worker dyno picks up the message, calls Resend API, sends email. 7. Client gets back the full Booking JSON including event details, venue, seat info.

---

**Q17: How would you scale this system to 10× the current load?**

> The web API is already stateless — add more Heroku dynos (or Kubernetes pods) behind the load balancer. The database is the main bottleneck at scale: add a read replica for the availability queries, keep writes on the primary. The Redis cache already absorbs most read traffic. The Celery worker pool can scale horizontally — multiple worker dynos consuming from the same RabbitMQ queue. The `UNIQUE` constraint-based booking logic already scales horizontally because it doesn't require application-level state.

---

**Q18: What are the weaknesses of this system?**

> 1. No connection pooling at the application level — under very high concurrency, DB connections could exhaust (mitigated by NeonDB's built-in pgBouncer). 2. Heroku Eco dynos sleep after 30 min — cold start ~15s (acceptable for portfolio, not production). 3. The JWT doesn't support refresh tokens — users get logged out after 30 min. 4. No rate limiting on the booking endpoint — a bad actor could flood it. 5. Email only goes to the account owner's address due to Resend sandbox restrictions.

---

**Q19: How is authentication handled and what token format?**

> OAuth2 Password flow with JWT bearer tokens. Login sends `username + password` as form data to `POST /auth/token`, receives a JWT. The JWT payload contains `sub` (user email) and `role` (customer/organizer). Signed with HS256 using a `SECRET_KEY` env var. Subsequent requests include `Authorization: Bearer <token>`. The `get_current_user` FastAPI dependency decodes it with `python-jose` on every request — no session state on the server.

---

**Q20: Why argon2 for password hashing?**

> Argon2 is memory-hard — it requires a significant amount of RAM to compute, which makes GPU-based brute-force attacks expensive. bcrypt is CPU-hard but GPUs can parallelise it cheaply. Argon2 won the Password Hashing Competition in 2015 and is the current recommended standard.

---

## Section E: Database

**Q21: Why PostgreSQL and not MongoDB for this use case?**

> The data has clear relational structure: users have bookings, bookings have tickets, tickets reference events and seats. The core correctness guarantee — `UNIQUE(event_id, seat_id)` — is a relational constraint. MongoDB doesn't have multi-document transactions that are as mature and you'd have to implement the uniqueness guarantee at the application layer, which is exactly the race-prone approach I'm avoiding.

---

**Q22: Explain the database schema relationships.**

> `user` 1→N `booking` (one user has many bookings). `booking` 1→N `ticket` (one booking has many tickets). `ticket` N→1 `event` and `ticket` N→1 `seat` (many tickets reference the same event/seat). `event` N→1 `venue` (many events at same venue). `seat` N→1 `venue` (many seats belong to a venue). The `UNIQUE(event_id, seat_id)` on ticket is the concurrency constraint — one ticket per seat per event, across all bookings.

---

**Q23: What is N+1 query problem and how do you avoid it?**

> N+1 is when you query a parent (1 query) then query each child separately (N queries). For example: fetch 10 bookings, then for each booking fetch its tickets separately = 11 queries. I avoid it with SQLAlchemy `joinedload`: `joinedload(Booking.tickets).joinedload(Ticket.seat)`. This generates a single SQL `JOIN` query that loads all related data in one round-trip.

---

**Q24: How do Alembic migrations work?**

> Alembic tracks schema changes as versioned Python files. Each file has an `upgrade()` (applies the change) and `downgrade()` (reverts it). `alembic revision --autogenerate` compares the SQLAlchemy models to the current DB schema and generates the migration automatically. `alembic upgrade head` applies all pending migrations. The migration history is stored in the `alembic_version` table in the DB itself.

---

## Section F: FastAPI & Python

**Q25: What is FastAPI's dependency injection and why is it useful?**

> `Depends()` is FastAPI's DI system. You declare dependencies as function arguments — FastAPI resolves them automatically before calling your endpoint. For example `db: Session = Depends(get_db)` creates a DB session for the request and closes it after. `current_user: User = Depends(get_current_user)` decodes the JWT and loads the user. This makes code testable (you can override dependencies in tests), avoids repetition (auth logic is in one place), and handles cleanup automatically via `yield`.

---

**Q26: What is Pydantic and what does it do in this project?**

> Pydantic is the validation and serialisation library FastAPI is built on. Every request body is a Pydantic `BaseModel` — FastAPI validates the incoming JSON against it automatically and returns a 422 if it doesn't match. Response models are also Pydantic — FastAPI serialises the SQLAlchemy ORM object into the defined schema. `Pydantic Settings` is used for config — it reads env vars and `.env` file and validates them at startup (fail-fast if `DATABASE_URL` is missing).

---

**Q27: What is the difference between `db.flush()` and `db.commit()`?**

> `flush()` sends the SQL to the database within the current transaction but does not commit — the changes are visible to other queries in the same session but not to other sessions/transactions. I use `flush()` after `db.add(booking)` to get the auto-generated `booking.id` (from the DB sequence) so I can assign it to tickets, without committing yet. Then `commit()` makes all changes permanent and releases locks.

---

## Section G: Production & Ops

**Q28: What bugs did you hit in production?**

> Three significant ones: 1. CORS — the frontend is on a Vercel preview URL that changes on every deploy. Fixed by adding `allow_origin_regex=r"https://.*\.vercel\.app"` to CORS middleware. 2. Celery 500s — having a Redis result backend caused Celery to open a pub/sub connection on every `.delay()` call. Upstash doesn't support pub/sub the same way, so every booking POST failed. Fixed by setting `backend=None`. 3. Resend sandbox — free tier only allows sending to the account owner's email. Fixed by adding `RESEND_TO_OVERRIDE` env var as a workaround.

---

**Q29: How do you run the concurrency tests?**

> `pytest tests/test_concurrency.py -v`. The test connects to `TEST_DATABASE_URL` (a separate test DB), creates its own fixtures with real commits, and cleans up with DELETE after. It uses `pytest-asyncio` for `asyncio.gather` and `httpx.AsyncClient` with ASGITransport (no real HTTP server needed — it calls the FastAPI app in-process). The output is saved to `proof/concurrency_test_output.txt`.

---

**Q30: How would you add rate limiting to the booking endpoint?**

> I'd add a Redis-based rate limiter as a FastAPI dependency. On each request, increment a counter keyed by `user_id` with a 60-second TTL: `redis.incr(f"rate:{user_id}")` + `redis.expire(...)`. If the counter exceeds the limit (e.g. 10 bookings/minute), return 429. A cleaner option is `slowapi` (a FastAPI wrapper around limits) which handles this declaratively with a decorator. Redis `INCR` is atomic so it works correctly across multiple web dynos.

---

**Q31: What would you add next to make this production-ready?**

> 1. Refresh tokens (short-lived access tokens, long-lived refresh). 2. Rate limiting on auth and booking endpoints. 3. A verified email domain so confirmations go to real users. 4. Webhook from Resend for bounce/delivery tracking. 5. An admin panel for organizers to view booking analytics. 6. Background job to expire/cancel unpaid bookings. 7. OpenTelemetry traces so you can see the full request span including DB queries and cache hits.

---

## Quick-fire answers (for rapid-fire rounds)

| Question | Answer |
|----------|--------|
| What port does Heroku inject? | `$PORT` env var, dynamic |
| Why `python:3.12-slim` not `alpine`? | Alpine has musl libc; many Python packages need glibc. Slim is smaller than full, compatible with all packages |
| What's the JWT algorithm? | HS256 (HMAC-SHA256) |
| Where are secrets stored? | Heroku config vars (env vars), never in code |
| What's the cache TTL? | 300 seconds (5 min) |
| What queue does Celery use? | Default `celery` queue |
| What does `--autogenerate` do in Alembic? | Diffs SQLAlchemy models against DB and generates migration |
| Why `joinedload` not `lazy`? | Lazy loading triggers N+1 queries; `joinedload` does one JOIN |
| What status code for double-booking? | 409 Conflict |
| What status code for wrong role? | 403 Forbidden |
| What status code for bad JWT? | 401 Unauthorized |
