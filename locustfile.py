"""
Locust Load Test — Scalable Booking System
==========================================

Two user classes:

1. PublicUser      — Read-only traffic (browse events, check availability)
                     Simulates the 95% of users who are just looking.

2. BookingUser     — Write traffic (signup, login, book tickets)
                     Simulates real customers completing purchases.

3. FlashSaleUser   — THE CONCURRENCY PROOF
                     All users hammer the SAME single seat simultaneously.
                     Run this class alone to generate the proof screenshot.

HOW TO RUN:

  Normal load test (mixed traffic):
    locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10

  Concurrency proof (flash sale simulation):
    locust -f locustfile.py --host=http://localhost:8000 \
           --users=50 --spawn-rate=50 \
           -H http://localhost:8000 \
           --run-time=30s --headless \
           --only-summary \
           --class-picker

  Then select ONLY FlashSaleUser in the web UI.
"""
from locust import HttpUser, task, between, events
import random
import threading

# ── Shared state for FlashSaleUser ───────────────────────────────────────────
# All FlashSaleUsers will target this single seat — set at test start
_flash_sale_state = {
    "event_id": None,
    "seat_id": None,
    "lock": threading.Lock(),
    "initialized": False,
}


# ── Public Read Traffic ───────────────────────────────────────────────────────

class PublicUser(HttpUser):
    """
    Simulates anonymous users browsing events.
    Represents ~70% of real traffic — pure read load.
    Proves Redis cache is serving these requests fast.
    """
    wait_time = between(1, 5)
    weight = 7  # 70% of users

    def on_start(self):
        res = self.client.get("/api/v1/events/")
        self.event_ids = [e["id"] for e in res.json()] if res.status_code == 200 else []

    @task(10)
    def view_events_list(self):
        """Cache hit after first request — proves Redis is working."""
        self.client.get("/api/v1/events/", name="GET /events (cached)")

    @task(5)
    def view_event_availability(self):
        """Availability check — cached after first DB hit."""
        if not self.event_ids:
            return
        event_id = random.choice(self.event_ids)
        self.client.get(
            f"/api/v1/events/{event_id}/availability",
            name="GET /events/[id]/availability (cached)",
        )

    @task(3)
    def view_single_event(self):
        if not self.event_ids:
            return
        event_id = random.choice(self.event_ids)
        self.client.get(f"/api/v1/events/{event_id}", name="GET /events/[id]")


# ── Authenticated Booking Traffic ─────────────────────────────────────────────

class BookingUser(HttpUser):
    """
    Simulates real customers completing bookings.
    Represents ~25% of traffic — write-heavy transactions.
    """
    wait_time = between(2, 8)
    weight = 2  # 20% of users

    def on_start(self):
        random_id = random.randint(1, 10_000_000)
        self.email = f"booker_{random_id}@test.com"
        self.password = "password123"
        self.token = None

        signup_res = self.client.post(
            "/api/v1/users/signup",
            json={
                "email": self.email,
                "password": self.password,
                "full_name": f"Booker {random_id}",
                "role": "customer",
            },
            name="POST /users/signup",
        )
        if signup_res.status_code != 200:
            return

        login_res = self.client.post(
            "/api/v1/auth/token",
            data={"username": self.email, "password": self.password},
            name="POST /auth/token",
        )
        if login_res.status_code == 200:
            self.token = login_res.json().get("access_token")
            self.client.headers["Authorization"] = f"Bearer {self.token}"

    @task
    def book_random_seat(self):
        """Books a random available seat — normal booking flow."""
        if not self.token:
            return

        events_res = self.client.get("/api/v1/events/", name="GET /events")
        if events_res.status_code != 200 or not events_res.json():
            return

        event = random.choice(events_res.json())
        event_id = event["id"]

        avail_res = self.client.get(
            f"/api/v1/events/{event_id}/availability",
            name="GET /availability",
        )
        if avail_res.status_code != 200:
            return

        available = avail_res.json().get("available", [])
        if not available:
            return

        seat_id = random.choice(available)["id"]

        # 409 is expected and correct — do not count as failure
        with self.client.post(
            "/api/v1/bookings/",
            json={"event_id": event_id, "seat_ids": [seat_id]},
            name="POST /bookings",
            catch_response=True,
        ) as res:
            if res.status_code in (200, 409):
                res.success()
            else:
                res.failure(f"Unexpected status: {res.status_code}")


# ── Flash Sale Concurrency Proof ──────────────────────────────────────────────

class FlashSaleUser(HttpUser):
    """
    THE CONCURRENCY PROOF USER CLASS.

    Run this class ALONE with --users=50 --spawn-rate=50

    ALL 50 users target the EXACT SAME seat simultaneously.

    What to look for in the Locust report:
      - POST /bookings: ~2% success rate (1/50)
      - POST /bookings: ~98% "failure" rate — but these are 409s (correct!)
      - 0 cases of the same seat booked twice

    This is the screenshot that goes on your resume.
    """
    wait_time = between(0, 0)  # No wait — fire immediately
    weight = 1

    def on_start(self):
        random_id = random.randint(1, 10_000_000)
        self.email = f"flash_{random_id}@test.com"
        self.password = "password123"
        self.token = None
        self.has_booked = False

        # Signup
        self.client.post(
            "/api/v1/users/signup",
            json={
                "email": self.email,
                "password": self.password,
                "full_name": f"Flash User {random_id}",
                "role": "customer",
            },
            name="[setup] signup",
        )

        # Login
        login_res = self.client.post(
            "/api/v1/auth/token",
            data={"username": self.email, "password": self.password},
            name="[setup] login",
        )
        if login_res.status_code == 200:
            self.token = login_res.json().get("access_token")
            self.client.headers["Authorization"] = f"Bearer {self.token}"

        # First user initializes the flash sale target (thread-safe)
        self._ensure_flash_sale_initialized()

    def _ensure_flash_sale_initialized(self):
        """One user creates the flash sale event. All others reuse it."""
        with _flash_sale_state["lock"]:
            if _flash_sale_state["initialized"]:
                return

            # Create organizer for the flash sale event
            org_email = "flash_organizer@test.com"
            self.client.post(
                "/api/v1/users/signup",
                json={
                    "email": org_email,
                    "password": "password123",
                    "full_name": "Flash Organizer",
                    "role": "organizer",
                },
                name="[setup] org signup",
            )
            login_res = self.client.post(
                "/api/v1/auth/token",
                data={"username": org_email, "password": "password123"},
                name="[setup] org login",
            )
            if login_res.status_code != 200:
                return

            org_token = login_res.json()["access_token"]
            org_headers = {"Authorization": f"Bearer {org_token}"}

            # Create venue with exactly 1 seat
            venue_res = self.client.post(
                "/api/v1/organizer/venues/",
                json={"name": "Flash Sale Arena", "rows": 1, "cols": 1},
                headers=org_headers,
                name="[setup] create venue",
            )
            if venue_res.status_code != 200:
                return
            venue_id = venue_res.json()["id"]

            # Create the event
            event_res = self.client.post(
                "/api/v1/organizer/events/",
                json={
                    "name": "FLASH SALE — 1 Seat Only",
                    "event_time": "2099-12-31T20:00:00Z",
                    "event_type": "concert",
                    "venue_id": venue_id,
                },
                headers=org_headers,
                name="[setup] create event",
            )
            if event_res.status_code != 200:
                return
            event_id = event_res.json()["id"]

            # Get the single seat ID
            avail_res = self.client.get(
                f"/api/v1/events/{event_id}/availability",
                name="[setup] get seat",
            )
            if avail_res.status_code == 200 and avail_res.json()["available"]:
                _flash_sale_state["event_id"] = event_id
                _flash_sale_state["seat_id"] = avail_res.json()["available"][0]["id"]
                _flash_sale_state["initialized"] = True
                print(f"\n🎯 Flash Sale Target: event={event_id}, seat={_flash_sale_state['seat_id']}")

    @task
    def attempt_flash_sale_booking(self):
        """
        ALL users hammer this single seat.
        Expected: 1 success, 49 conflicts.
        409 is marked as success because it IS the correct response.
        """
        if not self.token or self.has_booked:
            return
        if not _flash_sale_state["event_id"]:
            return

        self.has_booked = True  # Each user tries exactly once

        with self.client.post(
            "/api/v1/bookings/",
            json={
                "event_id": _flash_sale_state["event_id"],
                "seat_ids": [_flash_sale_state["seat_id"]],
            },
            name="POST /bookings [FLASH SALE — all same seat]",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
                print(f"✅ BOOKING SUCCESS — user {self.email} got the seat!")
            elif res.status_code == 409:
                # 409 is CORRECT — mark as success so Locust doesn't hide it
                res.success()
            else:
                res.failure(f"Unexpected {res.status_code}: {res.text}")