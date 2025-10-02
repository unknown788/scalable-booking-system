# locustfile.py
from locust import HttpUser, task, between
import random

class PublicUser(HttpUser):
    """
    Simulates a user browsing events without logging in.
    This represents the majority of your read-only traffic.
    """
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def on_start(self):
        # Fetch all events once to get a list of valid event IDs
        response = self.client.get("/api/v1/events/")
        self.event_ids = [event['id'] for event in response.json()]

    @task(10) # This task is 10 times more likely to be run
    def view_events_list(self):
        self.client.get("/api/v1/events/")

    @task(5) # This task is 5 times more likely
    def view_event_details_and_availability(self):
        if not self.event_ids:
            return
        event_id = random.choice(self.event_ids)
        self.client.get(f"/api/v1/events/{event_id}", name="/api/v1/events/[id]")
        self.client.get(f"/api/v1/events/{event_id}/availability", name="/api/v1/events/[id]/availability")

class BookingUser(HttpUser):
    """
    Simulates a user who signs up, logs in, and books a ticket.
    This is your critical, write-heavy transaction.
    """
    wait_time = between(2, 8)

    def on_start(self):
        # Each simulated user gets a unique email
        random_id = random.randint(1, 1000000)
        self.email = f"booker_{random_id}@test.com"
        self.password = "password123"

        # Signup
        self.client.post("/api/v1/users/signup", json={"email": self.email, "password": self.password})
        
        # Login
        response = self.client.post(
            "/api/v1/auth/token",
            data={"username": self.email, "password": self.password}
        )
        self.token = response.json()["access_token"]
        self.client.headers["Authorization"] = f"Bearer {self.token}"

    @task
    def book_ticket(self):
        # 1. Find an event and available seats
        response = self.client.get("/api/v1/events/")
        events = response.json()
        if not events:
            return
        event = random.choice(events)
        event_id = event['id']

        response = self.client.get(f"/api/v1/events/{event_id}/availability")
        availability = response.json()
        if not availability['available']:
            return
        
        # 2. Select one seat to book
        seat_to_book = availability['available'][0]['id']

        # 3. Perform the booking
        self.client.post(
            "/api/v1/bookings/",
            json={"event_id": event_id, "seat_ids": [seat_to_book]},
            name="/api/v1/bookings/"
        )
