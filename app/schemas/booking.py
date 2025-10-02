from pydantic import BaseModel
from typing import List
from datetime import datetime
from .event import Seat  # Re-use the Seat schema we already created


class Ticket(BaseModel):
    id: int
    price: float
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
