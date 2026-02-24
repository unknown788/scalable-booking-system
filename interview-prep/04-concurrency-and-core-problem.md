# 04 — Concurrency & The Core Problem

This is the most important doc. Every SDE-2 interview for this project will start here.

---

## The problem in one sentence

Two users click "Book" on the same seat at the same millisecond. Without special handling, both succeed — the same seat is sold twice.

---

## Why naive implementations fail

### Naive approach: read → check → write

```python
# THIS IS WRONG — DO NOT DO THIS
def book_seat(event_id, seat_id, user_id):
    existing = db.query(Ticket).filter_by(event_id=event_id, seat_id=seat_id).first()
    if existing:
        raise HTTPException(409, "Already booked")
    # BUG: another request can book between the check above and the insert below
    db.add(Ticket(event_id=event_id, seat_id=seat_id, user_id=user_id))
    db.commit()
```

The gap between the `SELECT` and the `INSERT` is called a **TOCTOU race** (Time Of Check, Time Of Use). Under concurrency:

```
User A: SELECT → not found
User B: SELECT → not found          ← same gap, both see "available"
User A: INSERT → succeeds ✓
User B: INSERT → succeeds ✓         ← double booking!
```

No amount of Python-level checks can fix this because Python runs on multiple threads/processes across multiple dynos, and the check and the write are two separate database round-trips.

---

## Why application-level locks also fail

### Option 1: Python threading.Lock

- Only works within a single process. Two Heroku dynos = two separate processes = two separate locks = zero protection.

### Option 2: Redis SETNX distributed lock

```python
# Still fragile
if redis.setnx(f"lock:seat:{seat_id}", 1):
    redis.expire(f"lock:seat:{seat_id}", 5)
    try:
        # book the seat
    finally:
        redis.delete(f"lock:seat:{seat_id}")
else:
    raise HTTPException(409)
```

Problems:
- Lock holder can die after booking but before deleting lock → seat stays locked forever (or until TTL expires)
- Redis and PostgreSQL are two separate systems — no atomicity between them
- Adds a round-trip to Redis on every booking
- If Redis goes down, all bookings fail
- Requires careful TTL tuning

### Option 3: SELECT FOR UPDATE (pessimistic locking)

```sql
SELECT * FROM seat WHERE id = X FOR UPDATE;
-- other transactions block here
INSERT INTO ticket ...;
COMMIT;  -- lock released
```

This works but serialises all bookings through a single DB lock. Under high load it creates a queue at the DB and destroys throughput.

---

## The actual solution: database-enforced uniqueness

The `ticket` table has a composite unique constraint:

```python
# app/models/booking.py
class Ticket(Base):
    __tablename__ = "ticket"
    __table_args__ = (
        UniqueConstraint("event_id", "seat_id", name="_event_seat_uc"),
    )
    id         = Column(Integer, primary_key=True)
    price      = Column(Numeric(10, 2))
    booking_id = Column(Integer, ForeignKey("booking.id"))
    event_id   = Column(Integer, ForeignKey("event.id"))
    seat_id    = Column(Integer, ForeignKey("seat.id"))
```

This means: **PostgreSQL will only ever allow one row with the same `(event_id, seat_id)` pair**. This is enforced at the storage engine level, inside a single atomic transaction, regardless of how many application servers are running.

### Why this works

```
User A: BEGIN; INSERT INTO ticket (event_id=5, seat_id=101) ...
User B: BEGIN; INSERT INTO ticket (event_id=5, seat_id=101) ...

PostgreSQL internally:
  - A's INSERT acquires a row-level lock on the new row
  - B's INSERT tries to insert the same key → waits for A
  - A: COMMIT → lock released, constraint passes
  - B: COMMIT → constraint VIOLATION → PostgreSQL raises IntegrityError
```

The database handles the concurrency. The application just catches `IntegrityError` and returns 409.

```python
try:
    db.add_all(tickets)
    db.commit()   # ← constraint enforced HERE, atomically
except IntegrityError:
    db.rollback()
    raise HTTPException(409, "Seat already booked")
```

### Why this is better than all the alternatives

| Property | App Lock | Redis Lock | SELECT FOR UPDATE | UniqueConstraint |
|----------|----------|------------|-------------------|-----------------|
| Multi-process safe | ❌ | ✅ | ✅ | ✅ |
| Atomic with DB | ❌ | ❌ | ✅ | ✅ |
| Works if Redis down | ❌ | ❌ | ✅ | ✅ |
| No serialisation bottleneck | ✅ | ✅ | ❌ | ✅ |
| Zero extra infrastructure | ✅ | ❌ | ✅ | ✅ |
| Horizontally scalable | ❌ | ✅ | ❌ | ✅ |

The `UniqueConstraint` is the only approach that is atomic, multi-process safe, and doesn't serialize throughput.

---

## The test: `test_concurrent_booking_only_one_succeeds`

Located in `tests/test_concurrency.py`.

### What it does

1. Creates a venue with **exactly 1 seat** (1 row × 1 col)
2. Creates an event at that venue
3. Creates **50 customer users** (simulating 50 concurrent people)
4. Fires **50 simultaneous HTTP requests** using `asyncio.gather` — all try to book the same single seat
5. Asserts the outcome

### Why real commits are required

The test does NOT use the standard pytest `db` fixture (which wraps in a single rolled-back transaction). It uses real `COMMIT` calls to the test DB. This is critical because:
- The `UniqueConstraint` race only plays out across **separate committed transactions**
- A single un-committed transaction would never see the constraint violation from concurrent requests

### Expected outcome

```
Results:
  Total requests:   50
  Successes (200):   1   ← exactly one booking goes through
  Conflicts (409):  49   ← all others get "seat already booked"

Database check:
  Tickets for this seat: 1  ← zero double bookings
```

### This is your proof

When an interviewer asks "how do you know it works?" — this test is the answer. 50 concurrent users, real DB transactions, exactly 1 winner. The output is saved to `proof/concurrency_test_output.txt`.

---

## Interview one-liner

> "I solve the double-booking problem at the database layer using a `UNIQUE(event_id, seat_id)` constraint on the tickets table. PostgreSQL's transaction engine makes the INSERT atomic — the first writer wins, all others get an IntegrityError which I surface as HTTP 409. No application-level locks, no Redis distributed locks, no serialization bottleneck. I proved it works with a test that fires 50 concurrent requests at a single seat and asserts exactly 1 success."

---

## Follow-up questions to prepare for

**Q: What if two seats are booked in the same request?**
The `for seat_id in booking_in.seat_ids` loop adds all tickets before `db.commit()`. If any one ticket violates the constraint, the entire transaction rolls back — partial bookings are impossible.

**Q: What's the ACID property this relies on?**
**Atomicity** (the whole transaction commits or rolls back) and **Isolation** (concurrent transactions don't see each other's uncommitted writes). PostgreSQL's default isolation level is `READ COMMITTED`, which is sufficient here because the constraint check happens at commit time.

**Q: Could you use optimistic locking instead?**
Optimistic locking (version numbers) works for update conflicts but not for insert conflicts. Since we're inserting new rows, the `UNIQUE` constraint is the natural mechanism.

**Q: What happens under extremely high load — will the DB become a bottleneck?**
Unlike `SELECT FOR UPDATE` which serialises all bookings through a lock queue, a `UNIQUE` constraint only conflicts when two requests try to book the **same seat**. Requests for different seats never block each other. This scales horizontally.
