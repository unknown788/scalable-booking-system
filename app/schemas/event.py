from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.event import EventType  # Import the enum from your model

# Schema for Venue


class VenueBase(BaseModel):
    name: str
    rows: int
    cols: int


class VenueCreate(VenueBase):
    pass


class Venue(VenueBase):
    id: int

    class Config:
        from_attributes = True

# Schema for Event
class EventBase(BaseModel):
    name: str
    description: Optional[str] = None
    event_time: datetime
    event_type: EventType
    venue_id: int


class EventCreate(EventBase):
    pass


class Event(EventBase):
    id: int
    organizer_id: int
    venue: Venue  # Nest the full Venue object in the response

    class Config:
        from_attributes = True


# Schema for a single Seat
class Seat(BaseModel):
    id: int
    row: str
    number: int

    class Config:
        from_attributes = True

# Schema for event availability response


class EventAvailability(BaseModel):
    total_seats: int
    available_seats: int
    booked_seats: int
    available: List[Seat]
    booked: List[Seat]
