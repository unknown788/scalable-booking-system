from pydantic import BaseModel
from typing import List
from datetime import datetime
from decimal import Decimal
from .event import Seat, Event  # Re-use the Seat and Event schemas


class Ticket(BaseModel):
    id: int
    price: Decimal
    seat: Seat
    event: Event  # full event (name, venue, event_time, event_type)

    class Config:
        from_attributes = True

# Properties to receive via API on creation


class BookingCreate(BaseModel):
    event_id: int
    seat_ids: List[int]

# Properties to return to client


class Booking(BaseModel):
    id: int
    booking_time: datetime
    tickets: List[Ticket] = []

    class Config:
        from_attributes = True
