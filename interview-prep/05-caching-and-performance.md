# 05 — Caching & Performance

---

## Why caching is needed here

The most-read endpoint in the system is `GET /events/{id}/availability`. During a load test:
- 80 concurrent users hit this endpoint repeatedly
- Each DB query touches 2 tables (seats + tickets), does a set-difference, and serialises to JSON
- Without cache: every request hits PostgreSQL → ~148 ms p50 latency

With a Redis cache in front: ~8.9 ms p50 (16.6× faster), because Redis is in-memory and the response is a pre-serialised JSON blob.

---

## The pattern: read-through cache

```
Request → app
  ↓
get_from_cache("availability:{event_id}")
  ↓ HIT                    ↓ MISS
return cached JSON         query PostgreSQL
(~8 ms)                    build availability dict
                           set_to_cache(..., ex=300)
                           return result
                           (~148 ms)
```

This is called **read-through** caching — the application checks the cache before going to the DB. The cache is populated on the first miss and then served for all subsequent requests until TTL expires or the cache is explicitly invalidated.

---

## Cache key design

Key: `"availability:{event_id}"`

Examples:
- `availability:5` → availability for event ID 5
- `availability:22` → availability for event ID 22

Simple, predictable, easy to invalidate. No namespace collision risk because the only thing stored in this Redis instance is availability data and metric counters.

---

## TTL = 300 seconds (5 minutes)

Why 5 minutes?
- Seat availability changes only when a booking is made
- Bookings are far less frequent than availability reads
- If a seat gets booked, the cache is **explicitly invalidated** immediately — so 5 min TTL is a safety net, not the primary freshness mechanism

```python
# booking_service.py — after db.commit()
cache_service.delete_from_cache(f"availability:{booking_in.event_id}")
```

This means the cache is **always fresh** after a booking — the 5 min TTL would only matter if this invalidation call somehow failed (Redis down, etc.).

---

## Cache is fault-tolerant

All Redis operations are wrapped in try/except. If Redis is down, the app falls back to the DB silently:

```python
def get_from_cache(key):
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.warning(f"CACHE ERROR: {e}")
        return None   # ← fall through to DB

def set_to_cache(key, value, ex=300):
    try:
        redis_client.set(key, json.dumps(value, default=str), ex=ex)
    except Exception as e:
        logger.warning(f"CACHE ERROR: {e}")
        # silently skip — app still works without cache
```

This is the correct design: **the cache is an optimisation, not a dependency**. The app must work without it.

---

## Metrics: proving the cache works

A dedicated endpoint `GET /api/v1/metrics` returns live stats accumulated in Redis counters:

```json
{
  "cache": {
    "cache_hits": 4821,
    "cache_misses": 38,
    "total_requests": 4859,
    "hit_rate_pct": 99.2,
    "avg_cache_ms": 8.4,
    "avg_db_ms": 87.3
  },
  "database": {
    "total_bookings": 142,
    "total_tickets": 218
  },
  "interpretation": {
    "speedup": "10.4x faster than DB",
    "story": "99.2% of availability checks served from Redis in 8ms vs 87ms from DB"
  }
}
```

### How the metrics are collected

Every `get_from_cache` call increments one of two Redis counters atomically:
```python
redis_client.incr("metrics:cache_hits")    # or
redis_client.incr("metrics:cache_misses")
```

Latencies are summed with `INCRBYFLOAT`:
```python
redis_client.incrbyfloat("metrics:cache_hit_total_ms", elapsed_ms)
```

The `/metrics` endpoint reads these counters and computes derived stats (hit rate %, average latencies, speedup ratio).

Using Redis `INCR` for counters is **atomic** — no race condition even with multiple workers incrementing simultaneously.

---

## Load test results (Locust)

Test configuration:
- 80 concurrent users
- Mix of GET /availability and POST /bookings
- Run for 60 seconds against production (Heroku)

Results:
- **Peak throughput**: 37 RPS
- **Cache hit rate**: 62.5%
- **Avg cache response**: 8.9 ms
- **Avg DB response**: 148 ms
- **Speedup**: 16.6×
- **0 failures** from the booking endpoint

Note: 62.5% hit rate (not 99%+) is because the load test hits multiple different events and the test DB has limited warm-up time. In a real scenario with a single popular event, hit rate would approach 99%+.

---

## The availability query (cache miss path)

When there's a cache miss, this is what runs:

```python
# Query 1: all seats for the venue, sorted
all_seats = (
    db.query(Seat)
    .filter(Seat.venue_id == event.venue_id)
    .order_by(Seat.row, Seat.number)
    .all()
)

# Query 2: set of booked seat IDs for this event (O(1) lookup later)
booked_seat_ids = {
    seat_id
    for seat_id, in db.query(Ticket.seat_id).filter(Ticket.event_id == event_id)
}

# O(n) list comprehension — no extra DB query
available = [s for s in all_seats if s.id not in booked_seat_ids]
booked    = [s for s in all_seats if s.id in booked_seat_ids]
```

Two queries total. The set comprehension makes the available/booked split O(n) rather than O(n²).

---

## Interview one-liner

> "I put a Redis read-through cache in front of the seat availability endpoint with a 5-minute TTL. The cache is explicitly invalidated on every booking commit, so it's always fresh. Under load test at 80 concurrent users I saw 16.6× speedup — 8.9 ms vs 148 ms — with zero impact on booking correctness because the cache only sits in front of reads, never writes. I also built a `/metrics` endpoint that uses Redis atomic counters to show live hit rate, average latencies, and speedup ratio."
