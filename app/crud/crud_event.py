from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone, time
from typing import Optional, List

from app.models.event import Venue, Event, Seat
from app.models.booking import Ticket
from app.schemas.event import VenueCreate, EventCreate


# ─────────────────────────────────────────
# VENUE
# ─────────────────────────────────────────

def create_venue(db: Session, *, venue_in: VenueCreate) -> Venue:
    """
    Creates a Venue and auto-generates all seats (rows x cols).
    Uses flush() to get venue.id before committing so seats
    can be linked in the same atomic transaction.
    """
    db_venue = Venue(
        name=venue_in.name,
        rows=venue_in.rows,
        cols=venue_in.cols,
    )
    db.add(db_venue)
    db.flush()  # get db_venue.id without committing yet

    seats_to_create = []
    for r in range(venue_in.rows):
        row_letter = chr(65 + r)  # 0→"A", 1→"B", 2→"C"
        for c in range(1, venue_in.cols + 1):
            seats_to_create.append(Seat(
                row=row_letter,
                number=c,
                venue_id=db_venue.id,
            ))

    db.add_all(seats_to_create)
    db.commit()
    db.refresh(db_venue)
    return db_venue


def get_venue(db: Session, venue_id: int) -> Optional[Venue]:
    return db.query(Venue).filter(Venue.id == venue_id).first()


def get_venues(db: Session, skip: int = 0, limit: int = 100) -> List[Venue]:
    return db.query(Venue).offset(skip).limit(limit).all()


# ─────────────────────────────────────────
# EVENT
# ─────────────────────────────────────────

def create_event(db: Session, *, event_in: EventCreate, organizer_id: int) -> Event:
    """
    Raw DB insert only. No caching logic here.
    Always call via event_service.create_event() which handles
    cache invalidation and primes the availability cache.
    """
    db_event = Event(
        name=event_in.name,
        description=event_in.description,
        event_time=event_in.event_time,
        event_type=event_in.event_type,
        venue_id=event_in.venue_id,
        organizer_id=organizer_id,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_event(db: Session, event_id: int) -> Optional[Event]:
    """
    Fetches a single event with its venue eagerly loaded.
    joinedload prevents N+1 queries when accessing event.venue.
    """
    return (
        db.query(Event)
        .options(joinedload(Event.venue))
        .filter(Event.id == event_id)
        .first()
    )


def get_events(db: Session, skip: int = 0, limit: int = 100) -> List[Event]:
    """
    Returns upcoming events (today onwards), ordered by event_time.
    Pure DB query — no caching. Caching is handled by event_service layer.
    """
    today_utc = datetime.now(timezone.utc).date()
    start_of_today_utc = datetime.combine(today_utc, time.min, tzinfo=timezone.utc)

    return (
        db.query(Event)
        .options(joinedload(Event.venue))
        .filter(Event.event_time >= start_of_today_utc)
        .order_by(Event.event_time)
        .offset(skip)
        .limit(limit)
        .all()
    )
