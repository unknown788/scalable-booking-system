from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app import schemas
from app.db import deps
from app.services import event_service   # <-- use service for all event ops
from app.crud import crud_event          # <-- keep only for get_venues

router = APIRouter()


@router.get("/events/", response_model=List[schemas.Event])
def read_events(db: Session = Depends(deps.get_db)):
    """Retrieve a list of upcoming events."""
    return event_service.get_all_events(db)


@router.get("/events/{event_id}", response_model=schemas.Event)
def read_event(*, db: Session = Depends(deps.get_db), event_id: int):
    """Get details for a specific event."""
    return event_service.get_event(db, event_id=event_id)
    # event_service.get_event already raises 404 — no manual check needed


@router.get("/events/{event_id}/availability", response_model=schemas.EventAvailability)
def read_event_availability(*, db: Session = Depends(deps.get_db), event_id: int):
    """Get seat availability for a specific event. Served from Redis cache when possible."""
    return event_service.get_event_availability(db, event_id=event_id)


@router.get("/venues/", response_model=List[schemas.Venue])
def read_venues(db: Session = Depends(deps.get_db), skip: int = 0, limit: int = 100):
    """Retrieve all venues."""
    return crud_event.get_venues(db, skip=skip, limit=limit)
