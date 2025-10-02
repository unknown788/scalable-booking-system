import redis
import json
from app.core.config import settings
from app.db.cache import redis_client
from app.services import cache_service
from app import schemas

from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone, time
from typing import Optional, List

from app.models.event import Venue, Event
from app.schemas.event import VenueCreate, EventCreate
from app.models.event import Venue, Event, Seat
from app.models.booking import Ticket

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

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
    db_event = Event(**event_in.model_dump(), organizer_id=organizer_id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # When a new event is created, the list of all events is now outdated.
    cache_service.delete_from_cache("events_list")

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
    # Get the current date in UTC
    today_utc = datetime.now(timezone.utc).date()
    # Get the moment the current UTC day started
    start_of_today_utc = datetime.combine(
        today_utc, time.min, tzinfo=timezone.utc)

    # For simplicity, we'll only cache the default first page of events
    if skip == 0 and limit == 100:
        cache_key = "events_list"
        cached_data = cache_service.get_from_cache(cache_key)
        if cached_data:
            # Pydantic can re-create the models from the list of dicts
            return cached_data

    # If miss, get from DB
    events = (
        db.query(Event)
        # Eager load venue to prevent N+1 queries
        .options(joinedload(Event.venue))
        .filter(Event.event_time >= start_of_today_utc)
        .order_by(Event.event_time)
        .offset(skip)
        .limit(limit)
        .all()
    )

    if skip == 0 and limit == 100:
        # Pydantic models need to be converted to dicts for JSON serialization
        # This is a good place to use a schema for serialization
        events_dicts = [schemas.Event.from_orm(e).dict() for e in events]
        cache_service.set_to_cache(
            "events_list", events_dicts, ex=60)  # 1-minute cache

    return events


# CRUD for getting event availability


def get_event_availability(db: Session, event_id: int) -> Optional[dict]:
    cache_key = f"availability:{event_id}"

    # 1. Try to get from cache first
    cached_data = cache_service.get_from_cache(cache_key)
    if cached_data:
        return cached_data

    # 2. If miss, get from DB (same logic as before)
    event = get_event(db=db, event_id=event_id)
    if not event:
        return None

    all_seats = db.query(Seat).filter(Seat.venue_id == event.venue_id).all()
    booked_ticket_query = db.query(Ticket.seat_id).filter(
        Ticket.event_id == event_id)
    booked_seat_ids = {seat_id for seat_id, in booked_ticket_query}

    available_seats_list = [
        seat for seat in all_seats if seat.id not in booked_seat_ids]
    booked_seats_list = [
        seat for seat in all_seats if seat.id in booked_seat_ids]

    # THE CRITICAL STEP: Convert SQLAlchemy objects to dictionaries before caching
    # This ensures the data is in a simple, JSON-serializable format.
    available_seats_dicts = [{"id": s.id, "row": s.row,
                              "number": s.number} for s in available_seats_list]
    booked_seats_dicts = [{"id": s.id, "row": s.row,
                           "number": s.number} for s in booked_seats_list]

    availability_data = {
        "total_seats": len(all_seats),
        "available_seats": len(available_seats_list),
        "booked_seats": len(booked_seats_list),
        "available": available_seats_dicts,
        "booked": booked_seats_dicts,
    }

    # 3. Store the clean, serializable data in the cache
    cache_service.set_to_cache(
        cache_key, availability_data, ex=300)  # 5-minute cache

    return availability_data
