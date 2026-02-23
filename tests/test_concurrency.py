"""
Concurrency Proof Test — Scalable Booking System
=================================================
This file is the PRIMARY PROOF for the resume claim:

  "The system prevents double-booking under concurrent load."

HOW IT WORKS:
  - Creates an event with exactly 1 seat (self-contained, no rollback fixture)
  - Fires N=50 HTTP requests simultaneously using asyncio.gather
  - Asserts: exactly 1 succeeds (HTTP 200), rest fail (HTTP 409)
  - Asserts: exactly 1 ticket row in DB — no data corruption

IMPORTANT — Why this test does NOT use the conftest `db` rollback fixture:
  The concurrency proof REQUIRES real commits to PostgreSQL so that the
  UniqueConstraint races play out across genuine transactions.  The `db`
  fixture wraps everything in a single un-committed transaction, which
  means every booking would share the same connection and never trigger
  the constraint across concurrent requests.  Instead we connect directly
  to TEST_DATABASE_URL with our own engine and clean up with DELETE afterwards.

This runs in CI on every push (see .github/main.yml).
The output is saved to proof/concurrency_test_output.txt automatically.
"""

import asyncio
import time
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import engine as _engine  # same engine the app uses

BASE_URL = "http://test"
NUM_CONCURRENT_USERS = 50

_Session = sessionmaker(bind=_engine)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _async_signup_and_login(email: str, password: str, role: str) -> str:
    """Create a user and return their JWT bearer token (async)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as ac:
        await ac.post("/api/v1/users/signup", json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "role": role,
        })
        res = await ac.post(
            "/api/v1/auth/token",
            data={"username": email, "password": password},
        )
        assert res.status_code == 200, f"Login failed for {email}: {res.text}"
        return res.json()["access_token"]


async def _async_create_single_seat_event(organizer_token: str) -> tuple:
    """
    Create a venue with exactly 1 seat (1 row × 1 col) and one event.
    Returns (event_id, seat_id, venue_id).
    """
    # Use timestamp so the name is unique on every run (test is re-runnable)
    ts = int(time.time())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as ac:
        venue_res = await ac.post(
            "/api/v1/organizer/venues/",
            json={"name": f"Concurrency Test Arena {ts}", "rows": 1, "cols": 1},
            headers={"Authorization": f"Bearer {organizer_token}"},
        )
        assert venue_res.status_code == 200, f"Venue creation failed: {venue_res.text}"
        venue_id = venue_res.json()["id"]

        event_res = await ac.post(
            "/api/v1/organizer/events/",
            json={
                "name": "Concurrency Proof Concert",
                "event_time": "2099-12-31T20:00:00Z",
                "event_type": "concert",
                "venue_id": venue_id,
            },
            headers={"Authorization": f"Bearer {organizer_token}"},
        )
        assert event_res.status_code == 200, f"Event creation failed: {event_res.text}"
        event_id = event_res.json()["id"]

        avail_res = await ac.get(f"/api/v1/events/{event_id}/availability")
        assert avail_res.status_code == 200
        data = avail_res.json()
        assert data["total_seats"] == 1, "Expected exactly 1 seat in this venue"
        seat_id = data["available"][0]["id"]

    return event_id, seat_id, venue_id


# ── The Core Test ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_concurrent_booking_only_one_succeeds():
    """
    PROOF: 50 concurrent users attempt to book the same single seat.
    Expected outcome:
      - Exactly 1 booking succeeds  (HTTP 200)
      - Exactly 49 receive conflict  (HTTP 409)
      - Database has exactly 1 ticket for this seat
      - NO double booking ever occurs

    Uses real commits to TEST_DATABASE_URL so PostgreSQL's UniqueConstraint
    races play out across genuine concurrent transactions.
    """
    DIVIDER = "=" * 60

    # ── Setup ─────────────────────────────────────────────────────
    organizer_token = await _async_signup_and_login(
        "organizer_proof@test.com", "password123", "organizer",
    )
    event_id, seat_id, venue_id = await _async_create_single_seat_event(organizer_token)

    # Create N unique customer accounts (one per concurrent user)
    customer_tokens = await asyncio.gather(
        *[
            _async_signup_and_login(
                f"concurrent_{i}@test.com", "password123", "customer"
            )
            for i in range(NUM_CONCURRENT_USERS)
        ]
    )

    print(f"\n{DIVIDER}")
    print(f"  CONCURRENCY PROOF: {NUM_CONCURRENT_USERS} users → 1 seat")
    print(f"  Event ID : {event_id}")
    print(f"  Seat  ID : {seat_id}")
    print(f"{DIVIDER}")

    # ── The Race ──────────────────────────────────────────────────
    # asyncio.gather fires ALL coroutines at the same time —
    # this is a true concurrent race, not sequential requests.
    # Each request opens its own AsyncClient / DB session so there
    # is no shared connection that would prevent the constraint race.

    async def attempt_booking(token: str, user_index: int) -> dict:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=BASE_URL,
        ) as ac:
            res = await ac.post(
                "/api/v1/bookings/",
                json={"event_id": event_id, "seat_ids": [seat_id]},
                headers={"Authorization": f"Bearer {token}"},
            )
            return {"user": user_index, "status": res.status_code}

    results = await asyncio.gather(
        *[attempt_booking(tok, i) for i, tok in enumerate(customer_tokens)]
    )

    # ── Tally Results ─────────────────────────────────────────────
    successes  = [r for r in results if r["status"] == 200]
    conflicts  = [r for r in results if r["status"] == 409]
    unexpected = [r for r in results if r["status"] not in (200, 409)]

    print(f"\n  RESULTS:")
    print(f"    ✅  HTTP 200 — Booking confirmed : {len(successes):>3}")
    print(f"    🔒  HTTP 409 — Seat already taken: {len(conflicts):>3}")
    print(f"    ❌  Unexpected status codes      : {len(unexpected):>3}")
    if unexpected:
        print(f"         → {[(r['user'], r['status']) for r in unexpected]}")

    # ── DB Integrity Check ────────────────────────────────────────
    # Query the real DB directly — the committed rows are what matter
    with _Session() as session:
        ticket_count = session.execute(
            text(
                "SELECT COUNT(*) FROM ticket "
                "WHERE event_id = :eid AND seat_id = :sid"
            ),
            {"eid": event_id, "sid": seat_id},
        ).scalar()

    print(f"\n  DB INTEGRITY CHECK:")
    print(f"    Ticket rows in DB for seat {seat_id}: {ticket_count} (expected: 1)")
    print(f"{DIVIDER}\n")

    # ── Cleanup — remove test data so the test is re-runnable ─────
    with _engine.connect() as conn:
        conn.execute(text(
            "DELETE FROM ticket WHERE event_id = :eid"
        ), {"eid": event_id})
        conn.execute(text(
            "DELETE FROM booking WHERE id NOT IN (SELECT booking_id FROM ticket)"
        ))
        conn.execute(text("DELETE FROM event WHERE id = :eid"), {"eid": event_id})
        conn.execute(text("DELETE FROM seat WHERE venue_id = :vid"), {"vid": venue_id})
        conn.execute(text("DELETE FROM venue WHERE id = :vid"), {"vid": venue_id})
        conn.execute(text(
            "DELETE FROM \"user\" WHERE email LIKE 'concurrent_%@test.com' "
            "OR email = 'organizer_proof@test.com'"
        ))
        conn.commit()

    # ── ASSERTIONS — the actual proof ────────────────────────────
    assert len(unexpected) == 0, (
        f"Unexpected HTTP responses: {[(r['user'], r['status']) for r in unexpected]}"
    )
    assert len(successes) == 1, (
        f"🚨 DOUBLE BOOKING: {len(successes)} requests got HTTP 200 for "
        f"the same seat. System is NOT concurrency-safe!"
    )
    assert len(conflicts) == NUM_CONCURRENT_USERS - 1, (
        f"Expected {NUM_CONCURRENT_USERS - 1} conflicts, got {len(conflicts)}"
    )
    assert ticket_count == 1, (
        f"🚨 DATA CORRUPTION: {ticket_count} ticket rows exist for 1 seat. "
        f"UniqueConstraint failed!"
    )

    print(f"  ✅ PROOF PASSED")
    print(f"     {NUM_CONCURRENT_USERS} concurrent users fired at 1 seat")
    print(f"     → Exactly 1 booking confirmed")
    print(f"     → Zero double-bookings in database")
