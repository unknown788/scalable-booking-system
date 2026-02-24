# 02 — Database & Data Model

This doc explains the schema, relationships, and the rationale behind data modeling.

---

## High-level tables

- `user`
  - id, full_name, email (unique), hashed_password, is_active, role (customer|organizer)
- `venue`
  - id, name (unique), rows, cols
- `seat`
  - id, row (string), number (int), venue_id
- `event`
  - id, name, description, event_time (timestamp), event_type, venue_id, organizer_id
- `booking`
  - id, booking_time, status (pending|confirmed|cancelled), user_id
- `ticket`
  - id, price, booking_id, event_id, seat_id
  - UniqueConstraint(event_id, seat_id)  <- core concurrency guard

---

## Important columns & constraints

- `user.email` is unique to allow login by email.
- `venue.name` is unique to avoid duplicate venues.
- `ticket` has a composite unique index on `(event_id, seat_id)` — this is the
  single most important design decision. It lets PostgreSQL enforce the
  "only-one-ticket-per-seat-per-event" invariant while the application can
  remain horizontally scalable.

---

## Row labels

- Seats store `row` as a `String` (e.g. "A", "B", "AA") so venues with >26
  rows are supported. `seed_prod.py` and `create_venue()` both generate
  alphabetic labels.

---

## Migrations

- Alembic is used. The initial schema is in `alembic/versions/902bb8897c35_initial_database_schema.py`.
- Migration practice: create a new migration file with `alembic revision --autogenerate -m "desc"`.

---

## Access patterns & indexes

- Most reads are for seat availability per event (reads all seats for the venue + tickets for the event).
- Indexes:
  - Primary keys on all id columns
  - `user.email` index unique
  - `seat` uses `venue_id` foreign key — the query uses `WHERE seat.venue_id = X` which benefits from this

---

## Reasoning: Why not application locks?

- Application-level locks (mutexes, Redis locks) are brittle in distributed systems — they require lease renewal, careful handling during process crashes, and can become a single point of failure.
- Let the database do what it's best at: enforcing invariants with atomic transactions and constraints. This keeps the application stateless and horizontally scalable.

---

## Test to prove correctness

See `tests/test_concurrency.py`. The test intentionally uses real DB commits and spawns 50 concurrent HTTP requests. The assertion is:
- Exactly 1 request gets HTTP 200 (success)
- Exactly 49 requests get HTTP 409 (conflict)
- Exactly 1 ticket row exists in DB after the test

This is the canonical "proof" you should memorise for interviews.
