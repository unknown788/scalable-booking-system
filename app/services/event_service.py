# app/services/event_service.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from datetime import datetime, timezone, time
from loguru import logger

from app.models.event import Venue, Event, Seat
from app.models.booking import Ticket
from app.schemas.event import VenueCreate, EventCreate
from app.services.cache_service import get_from_cache, set_to_cache, delete_from_cache, record_db_latency


# ─────────────────────────────────────────
# VENUE
# ─────────────────────────────────────────

def create_venue(db: Session, venue_in: VenueCreate) -> Venue:
    """Creates a venue and auto-generates all seats (rows x cols)."""
    try:
        venue = Venue(
            name=venue_in.name,
            rows=venue_in.rows,
            cols=venue_in.cols,
        )
        db.add(venue)
        db.flush()  # get venue.id without committing yet

        seats = []
        for row_num in range(venue_in.rows):
            row_letter = chr(65 + row_num)  # 0→"A", 1→"B", ...
            for col_num in range(1, venue_in.cols + 1):
                seats.append(Seat(
                    row=row_letter,
                    number=col_num,
                    venue_id=venue.id,
                ))

        db.add_all(seats)
        db.commit()
        db.refresh(venue)
        logger.info(f"Venue '{venue.name}' created with {len(seats)} seats")
        return venue

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A venue with the name '{venue_in.name}' already exists."
        )


def get_venue(db: Session, venue_id: int) -> Venue:
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


# ─────────────────────────────────────────
# EVENT
# ─────────────────────────────────────────

def create_event(db: Session, event_in: EventCreate, organizer_id: int) -> Event:
    """
    Creates an event, verifies venue exists, primes availability cache.
    Single commit, single eager-load query after commit.
    """
    get_venue(db, event_in.venue_id)  # raises 404 if venue doesn't exist

    event = Event(
        name=event_in.name,
        description=event_in.description,
        event_time=event_in.event_time,
        event_type=event_in.event_type,
        venue_id=event_in.venue_id,
        organizer_id=organizer_id,
    )
    db.add(event)
    db.commit()

    # Single query with joinedload — loads venue relationship for Pydantic serialization
    event = (
        db.query(Event)
        .options(joinedload(Event.venue))
        .filter(Event.id == event.id)
        .first()
    )

    # Invalidate stale events list cache + prime fresh availability cache
    delete_from_cache("events_list")
    _build_and_cache_availability(db, event.id)

    logger.info(f"Event '{event.name}' (id={event.id}) created by organizer {organizer_id}")
    return event


def get_event(db: Session, event_id: int) -> Event:
    """Fetches a single event with its venue eagerly loaded."""
    event = (
        db.query(Event)
        .options(joinedload(Event.venue))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def get_all_events(db: Session) -> list:
    """
    Returns all upcoming events as ORM objects.
    Always queries DB — ORM objects cannot be safely round-tripped
    through Redis, so caching here would require full deserialization.
    Availability caching (the expensive query) is handled separately.
    """
    today_utc = datetime.now(timezone.utc).date()
    start_of_today_utc = datetime.combine(today_utc, time.min, tzinfo=timezone.utc)

    return (
        db.query(Event)
        .options(joinedload(Event.venue))
        .filter(Event.event_time >= start_of_today_utc)
        .order_by(Event.event_time)
        .all()
    )


# ─────────────────────────────────────────
# AVAILABILITY
# ─────────────────────────────────────────

def get_event_availability(db: Session, event_id: int) -> dict:
    """
    Returns seat availability. Redis cache first, PostgreSQL fallback.
    Returned dict matches schemas.EventAvailability exactly.
    """
    cached = get_from_cache(f"availability:{event_id}")
    if cached:
        return cached
    import time as _time
    t0 = _time.monotonic()
    result = _build_and_cache_availability(db, event_id)
    record_db_latency((_time.monotonic() - t0) * 1000)
    return result


def _build_and_cache_availability(db: Session, event_id: int) -> dict:
    """
    Queries DB for availability, stores in Redis (5-min TTL), returns dict.
    Dict shape must match schemas.EventAvailability:
      { total_seats, available_seats, booked_seats, available: [Seat], booked: [Seat] }
    """
    event = get_event(db, event_id)  # raises 404 if not found

    all_seats = db.query(Seat).filter(Seat.venue_id == event.venue_id).all()

    # Set comprehension for O(1) lookup — single optimised query
    booked_seat_ids = {
        seat_id
        for seat_id, in db.query(Ticket.seat_id).filter(Ticket.event_id == event_id)
    }

    available_seats_list = [s for s in all_seats if s.id not in booked_seat_ids]
    booked_seats_list    = [s for s in all_seats if s.id in booked_seat_ids]

    availability_data = {
        "total_seats":     len(all_seats),
        "available_seats": len(available_seats_list),
        "booked_seats":    len(booked_seats_list),
        "available": [
            {"id": s.id, "row": s.row, "number": s.number}
            for s in available_seats_list
        ],
        "booked": [
            {"id": s.id, "row": s.row, "number": s.number}
            for s in booked_seats_list
        ],
    }

    set_to_cache(f"availability:{event_id}", availability_data, ex=300)
    return availability_data