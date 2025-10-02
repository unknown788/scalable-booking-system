from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# This test will cover the full end-to-end flow for a booking.


def test_full_user_booking_flow(client: TestClient, db: Session):
    # 1. Organizer Signup and Login
    organizer_data = {
        "email": "organizer1@example.com",
        "password": "organizer123",
        "full_name": "organizer1",
        "role": "organizer"
    }
    client.post("/api/v1/users/signup", json=organizer_data)

    login_res = client.post(
        "/api/v1/auth/token",
        data={"username": "organizer1@example.com", "password": "organizer123"}
    )
    organizer_token = login_res.json()["access_token"]
    organizer_headers = {"Authorization": f"Bearer {organizer_token}"}

    # 2. Organizer Creates a Venue and an Event
    venue_data = {"name": "Test Live Arena", "rows": 5, "cols": 10}
    venue_res = client.post("/api/v1/organizer/venues/",
                            json=venue_data, headers=organizer_headers)
    assert venue_res.status_code == 200
    venue_id = venue_res.json()["id"]

    event_data = {
        "name": "Live Concert",
        "event_time": "2025-12-25T20:00:00Z",
        "event_type": "concert",
        "venue_id": venue_id
    }
    event_res = client.post("/api/v1/organizer/events/",
                            json=event_data, headers=organizer_headers)
    assert event_res.status_code == 200
    event_id = event_res.json()["id"]

    # 3. Customer Signup and Login
    customer_data = {
        "email": "customer@example.com",
        "password": "$2b$12$w48KKfUamNpPER2FlbhBju2r5urM9QOGageWBuecRCsnh1eLoj2cG",
        "full_name": "customer 1",
        "role": "customer"
    }
    client.post("/api/v1/users/signup", json=customer_data)

    login_res = client.post(
        "/api/v1/auth/token",
        data={"username": "customer@example.com", "password": "$2b$12$w48KKfUamNpPER2FlbhBju2r5urM9QOGageWBuecRCsnh1eLoj2cG"}
    )
    customer_token = login_res.json()["access_token"]
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # 4. Customer views available seats for the event
    avail_res = client.get(f"/api/v1/events/{event_id}/availability")
    assert avail_res.status_code == 200
    availability = avail_res.json()
    assert availability["total_seats"] == 50  # 5 rows * 10 cols
    assert availability["available_seats"] == 50

    # Select the first two available seats for booking
    seats_to_book = [availability["available"][0]
                     ["id"], availability["available"][1]["id"]]

    # 5. Customer Creates a Booking
    booking_data = {"event_id": event_id, "seat_ids": seats_to_book}
    booking_res = client.post(
        "/api/v1/bookings/", json=booking_data, headers=customer_headers)

    # Assert Booking was successful
    assert booking_res.status_code == 200
    assert "id" in booking_res.json()
    assert len(booking_res.json()["tickets"]) == 2

    # 6. Verify that the booked seats are no longer available
    avail_res_after = client.get(f"/api/v1/events/{event_id}/availability")
    availability_after = avail_res_after.json()
    assert availability_after["available_seats"] == 48
    assert availability_after["booked_seats"] == 2
