from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import Optional, List

from app.models.event import Venue, Event
from app.schemas.event import VenueCreate, EventCreate
from app.models.event import Venue, Event, Seat
from app.models.booking import Ticket

# CRUD for Venue


def create_venue(db: Session, *, venue_in: VenueCreate) -> Venue:
    db_venue = Venue(name=venue_in.name, rows=venue_in.rows, cols=venue_in.cols)
    db.add(db_venue)
    db.flush()  # Use flush to get the db_venue.id before committing

    # Automatically create seats for the new venue
    seats_to_create = []
    for r in range(1, venue_in.rows + 1):
        for c in range(1, venue_in.cols + 1):
            # Using chr(64 + r) to get 'A', 'B', 'C'... for row labels
            seat = Seat(row=chr(64 + r), number=c, venue_id=db_venue.id)
            seats_to_create.append(seat)
    
    db.add_all(seats_to_create)
    db.commit()
    db.refresh(db_venue)
    return db_venue

# CRUD for Event


def create_event(db: Session, *, event_in: EventCreate, organizer_id: int) -> Event:
    # Create a dictionary from the pydantic model and add the organizer_id
    db_event = Event(**event_in.model_dump(), organizer_id=organizer_id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def create_venue(db: Session, *, venue_in: VenueCreate) -> Venue:
    db_venue = Venue(**venue_in.model_dump())
    db.add(db_venue)
    db.commit()
    db.refresh(db_venue)
    # Create all the seats for the new venue
    create_venue_seats(db=db, venue=db_venue)
    return db_venue


def create_venue_seats(db: Session, *, venue: Venue) -> None:
    """Generates Seat records for a given venue based on its rows and cols."""
    for r in range(1, venue.rows + 1):
        # We'll use letters for rows, e.g., A, B, C...
        row_letter = chr(ord('A') + r - 1)
        for c in range(1, venue.cols + 1):
            db_seat = Seat(row=row_letter, number=c, venue_id=venue.id)
            db.add(db_seat)
    db.commit()


# CRUD for reading venues
def get_venue(db: Session, venue_id: int) -> Optional[Venue]:
    return db.query(Venue).filter(Venue.id == venue_id).first()


def get_venues(db: Session, skip: int = 0, limit: int = 100) -> List[Venue]:
    return db.query(Venue).offset(skip).limit(limit).all()

# CRUD for reading events


def get_event(db: Session, event_id: int) -> Optional[Event]:
    # Use joinedload to efficiently fetch the related venue
    return db.query(Event).options(joinedload(Event.venue)).filter(Event.id == event_id).first()


def get_events(db: Session, skip: int = 0, limit: int = 100) -> List[Event]:
    # Filter for events that haven't happened yet and order them
    return (
        db.query(Event)
        .filter(Event.event_time >= datetime.utcnow())
        .order_by(Event.event_time)
        .offset(skip)
        .limit(limit)
        .all()
    )

# CRUD for getting event availability


def get_event_availability(db: Session, event_id: int) -> dict:
    event = get_event(db=db, event_id=event_id)
    if not event:
        return None

    # 1. Get all seats for the event's venue
    all_seats = db.query(Seat).filter(Seat.venue_id == event.venue_id).all()

    # 2. Get all seat IDs that have been booked for this specific event
    booked_seat_ids = {
        ticket.seat_id for ticket in db.query(Ticket).filter(Ticket.event_id == event_id).all()
    }

    # 3. Differentiate between available and booked seats
    available_seats_list = [
        seat for seat in all_seats if seat.id not in booked_seat_ids]
    booked_seats_list = [
        seat for seat in all_seats if seat.id in booked_seat_ids]

    return {
        "total_seats": len(all_seats),
        "available_seats": len(available_seats_list),
        "booked_seats": len(booked_seats_list),
        "available": available_seats_list,
        "booked": booked_seats_list,
    }
