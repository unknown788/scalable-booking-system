from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_full_user_booking_flow(client: TestClient, db: Session):
    # ── 1. Organizer Signup and Login ──────────────────────────────────────
    organizer_data = {
        "email": "organizer1@example.com",
        "password": "organizer123",       # plain text — create_user hashes it
        "full_name": "organizer1",
        "role": "organizer"
    }
    signup_res = client.post("/api/v1/users/signup", json=organizer_data)
    assert signup_res.status_code == 200

    login_res = client.post(
        "/api/v1/auth/token",
        data={"username": "organizer1@example.com", "password": "organizer123"}
    )
    assert login_res.status_code == 200
    organizer_token = login_res.json()["access_token"]
    organizer_headers = {"Authorization": f"Bearer {organizer_token}"}

    # ── 2. Organizer Creates a Venue ───────────────────────────────────────
    venue_data = {"name": "Test Live Arena", "rows": 5, "cols": 10}
    venue_res = client.post(
        "/api/v1/organizer/venues/", json=venue_data, headers=organizer_headers
    )
    assert venue_res.status_code == 200
    venue_id = venue_res.json()["id"]

    # ── 3. Organizer Creates an Event ──────────────────────────────────────
    event_data = {
        "name": "Live Concert",
        "event_time": "2099-12-25T20:00:00Z",   # far future — won't be filtered out
        "event_type": "concert",
        "venue_id": venue_id
    }
    event_res = client.post(
        "/api/v1/organizer/events/", json=event_data, headers=organizer_headers
    )
    assert event_res.status_code == 200
    event_id = event_res.json()["id"]

    # ── 4. Customer Signup and Login ───────────────────────────────────────
    customer_data = {
        "email": "customer@example.com",
        "password": "customer123",         # plain text — NOT a hash
        "full_name": "Customer One",
        "role": "customer"
    }
    signup_res = client.post("/api/v1/users/signup", json=customer_data)
    assert signup_res.status_code == 200

    login_res = client.post(
        "/api/v1/auth/token",
        data={"username": "customer@example.com", "password": "customer123"}
    )
    assert login_res.status_code == 200
    customer_token = login_res.json()["access_token"]
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # ── 5. Customer views available seats ─────────────────────────────────
    avail_res = client.get(f"/api/v1/events/{event_id}/availability")
    assert avail_res.status_code == 200
    availability = avail_res.json()
    assert availability["total_seats"] == 50        # 5 rows × 10 cols
    assert availability["available_seats"] == 50
    assert availability["booked_seats"] == 0

    seats_to_book = [
        availability["available"][0]["id"],
        availability["available"][1]["id"],
    ]

    # ── 6. Customer Books two seats ────────────────────────────────────────
    booking_res = client.post(
        "/api/v1/bookings/",
        json={"event_id": event_id, "seat_ids": seats_to_book},
        headers=customer_headers,
    )
    assert booking_res.status_code == 200
    booking_json = booking_res.json()
    assert "id" in booking_json
    assert len(booking_json["tickets"]) == 2

    # ── 7. Verify seats are now unavailable ────────────────────────────────
    avail_after_res = client.get(f"/api/v1/events/{event_id}/availability")
    assert avail_after_res.status_code == 200
    avail_after = avail_after_res.json()
    assert avail_after["available_seats"] == 48
    assert avail_after["booked_seats"] == 2

    # ── 8. Verify double-booking returns 409 ──────────────────────────────
    duplicate_res = client.post(
        "/api/v1/bookings/",
        json={"event_id": event_id, "seat_ids": seats_to_book},
        headers=customer_headers,
    )
    assert duplicate_res.status_code == 409
