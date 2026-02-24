# 03 — Backend Deep-Dive

Everything about how the FastAPI backend is structured, how requests flow, and why each piece is designed the way it is.

---

## Project layout

```
app/
  main.py            ← FastAPI app instance, CORS, router mounting
  api/v1/
    api.py           ← APIRouter: wires all endpoint routers together
    endpoints/
      auth.py        ← POST /auth/token
      users.py       ← POST /users/signup
      public.py      ← GET /events/, /events/{id}, /events/{id}/availability, /venues/
      bookings.py    ← GET /bookings/my, POST /bookings/
      events.py      ← POST /organizer/venues/, /organizer/events/
      metrics.py     ← GET /metrics
  core/
    config.py        ← Pydantic Settings — all env vars in one place
    security.py      ← argon2 password hashing, JWT create/verify
    celery_app.py    ← Celery instance config
  db/
    session.py       ← SQLAlchemy engine + SessionLocal
    deps.py          ← FastAPI dependencies: get_db, get_current_user, get_current_organizer
    cache.py         ← Redis client instance
  models/            ← SQLAlchemy ORM models
  schemas/           ← Pydantic request/response models
  services/          ← Business logic layer (booking_service, event_service, cache_service)
  crud/              ← Raw DB queries (no business logic)
  worker.py          ← Celery task: send_booking_confirmation
```

---

## All API endpoints

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/token` | None | Login — returns JWT |
| POST | `/api/v1/users/signup` | None | Register new user |

### Public (no auth required)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/events/` | None | List all upcoming events |
| GET | `/api/v1/events/{id}` | None | Get one event |
| GET | `/api/v1/events/{id}/availability` | None | Seat availability (cached) |
| GET | `/api/v1/venues/` | None | List all venues |

### Bookings (customer auth required)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/bookings/` | Bearer JWT | Create booking |
| GET | `/api/v1/bookings/my` | Bearer JWT | Get my bookings |

### Organizer (organizer role required)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/organizer/venues/` | Bearer JWT (organizer) | Create venue + auto-generate seats |
| POST | `/api/v1/organizer/events/` | Bearer JWT (organizer) | Create event |

### Observability

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/metrics` | None | Live cache + booking stats |

---

## Auth & JWT flow — step by step

1. **Signup**: `POST /users/signup` → password hashed with **argon2** via passlib → stored in `user.hashed_password`
2. **Login**: `POST /auth/token` → email+password in form body → verify argon2 hash → create JWT
3. **JWT payload**: `{ "sub": user.email, "role": "customer"|"organizer", "exp": <unix timestamp> }`
4. **Signing**: `HS256` algorithm with `SECRET_KEY` from env
5. **Expiry**: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 min) from config
6. **Protected route**: request sends `Authorization: Bearer <token>` header
7. **`get_current_user` dep**: decodes JWT with `python-jose`, extracts `sub` (email) + `role`, queries DB for user, returns `User` ORM object
8. **Role guard**: `get_current_organizer` dep calls `get_current_user` then checks `user.role == UserRole.organizer`, raises 403 if not

```
POST /auth/token
  form: username=email, password=...
    ↓
  crud_user.get_user_by_email()
  verify_password(plain, hashed)
    ↓
  create_access_token({"sub": email, "role": role})
    ↓
  returns {"access_token": "eyJ...", "token_type": "bearer"}
```

**Why argon2?** It's memory-hard — resistant to GPU brute-force attacks. Much stronger than bcrypt for modern threat models.

**Why not refresh tokens?** This is a portfolio project. In production you'd add a `refresh_token` endpoint and short-lived access tokens (5 min). The 30-min expiry is a tradeoff for simplicity.

---

## Dependency Injection pattern

FastAPI uses `Depends()` for DI. This is the chain for a protected booking endpoint:

```python
@router.post("/")
def create_booking(
    db: Session = Depends(get_db),                    # DB session
    booking_in: schemas.BookingCreate,                # request body (auto-validated)
    current_user: models.User = Depends(get_current_user),  # JWT → User
):
```

- `get_db` → yields a `SessionLocal()`, always closes in `finally`
- `get_current_user` → decodes JWT → queries user → returns `User` object
- `get_current_organizer` → calls `get_current_user` then checks role

The database session is **request-scoped** — a new session per request, closed after response. This is the standard SQLAlchemy pattern with FastAPI.

---

## Services layer vs CRUD layer

| Layer | Purpose | Example |
|-------|---------|---------|
| `crud/` | Raw DB queries, no business logic | `crud_user.get_user_by_email(db, email)` |
| `services/` | Business logic, orchestration, cache | `booking_service.create_new_booking(...)` |
| `endpoints/` | HTTP layer only — call service, return response | `return booking_service.create_new_booking(...)` |

**Why the separation?** Endpoints should be thin — just HTTP concerns (parsing request, returning response). Business logic (validate event exists, check seats, fire email) lives in services. Raw queries live in CRUD so they're reusable. This makes each layer independently testable.

---

## Booking creation — full flow

```
POST /api/v1/bookings/
  body: { event_id: 5, seat_ids: [101, 102] }
  header: Authorization: Bearer <token>

  1. get_current_user dep → JWT decoded → User loaded from DB
  2. booking_service.create_new_booking(db, booking_in, user_id)
     a. crud_event.get_event() → verify event exists (404 if not)
     b. crud_user.get_user() → load user for email address
     c. db.add(Booking(user_id=...))
     d. db.flush() → get booking.id without committing
     e. for each seat_id: db.add(Ticket(booking_id, event_id, seat_id, price))
     f. db.commit() ← PostgreSQL enforces UNIQUE(event_id, seat_id) HERE
        → IntegrityError if any seat already booked → rollback → 409
     g. Re-query booking with joinedload(tickets → seat, tickets → event → venue)
     h. cache_service.delete_from_cache("availability:{event_id}")
     i. send_booking_confirmation.delay(booking_id, user.email) ← async via RabbitMQ
  3. Return Booking schema (with full ticket + event + venue data)
```

---

## Seat availability — cache-first read pattern

```
GET /api/v1/events/{id}/availability

  1. cache_service.get_from_cache("availability:{event_id}")
     → HIT: return cached dict immediately (~8 ms)
     → MISS: continue to step 2

  2. _build_and_cache_availability(db, event_id)
     a. Query all seats for venue: WHERE seat.venue_id = event.venue_id
        ORDER BY seat.row, seat.number
     b. Query booked seat IDs: SELECT seat_id FROM ticket WHERE event_id = X
        (set comprehension for O(1) lookup)
     c. Compute available = all_seats - booked_seats
     d. cache_service.set_to_cache("availability:{event_id}", data, ex=300)
     e. Return data

  Cache TTL = 300 seconds (5 min)
  Cache is invalidated immediately when a booking is created.
```

---

## Settings / Config

All config is in `app/core/config.py` using **Pydantic Settings** (`pydantic-settings`).

```python
class Settings(BaseSettings):
    DATABASE_URL: str          # NeonDB connection string
    SECRET_KEY: str            # JWT signing key
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RABBITMQ_URL: str          # CloudAMQP
    REDIS_URL: str             # Upstash Redis
    ENVIRONMENT: str = "development"
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "booking-system@example.com"
    CORS_ORIGINS: str = ""     # comma-separated extra origins
```

Pydantic reads from **env vars** first, then `.env` file. All secrets are injected via Heroku config vars — never in code.

---

## CORS configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://404by.me", ...],
    allow_origin_regex=r"https://.*\.vercel\.app",  # all Vercel preview URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

The `allow_origin_regex` was added because Vercel generates unique preview deploy URLs (e.g. `frontend-abc123.vercel.app`) on every commit. Without this, CORS would block the frontend on every new deploy.

---

## Logging

`loguru` is used everywhere with structured JSON output in production:
```python
logger.remove()
logger.add(sys.stdout, serialize=True, enqueue=True)
```
`serialize=True` → JSON lines (structured logs, parseable by Heroku log drains)
`enqueue=True` → thread-safe async logging (doesn't block request handlers)

---

## Key design decisions to know

**Q: Why FastAPI and not Django/Flask?**
FastAPI is async-native, has automatic OpenAPI docs, and Pydantic validation built-in. For an API-first backend with real-time concurrency requirements, it's the right tool.

**Q: Why SQLAlchemy and not an async ORM?**
The bottleneck is the DB constraint race, not I/O wait — a sync ORM is fine. Adding async ORM complexity (SQLAlchemy async requires different session handling) would obscure the core architecture without real benefit at this scale.

**Q: Why separate web and worker dynos?**
The web dyno must respond fast. Email sending via Resend can take 200–800ms and can fail/retry. Putting it on a background worker keeps the booking API response under 50ms and makes retries reliable.
