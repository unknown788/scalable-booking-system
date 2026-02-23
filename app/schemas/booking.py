from pydantic import BaseModel
from typing import List
from datetime import datetime
from decimal import Decimal
from .event import Seat  # Re-use the Seat schema we already created


class Ticket(BaseModel):
    id: int
    price: Decimal  # matches Numeric(10,2) — Pydantic serializes Decimal correctly as number
    seat: Seat

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
