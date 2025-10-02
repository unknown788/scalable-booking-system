from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import schemas
from app.crud import crud_event
from app.db import deps

router = APIRouter()


@router.get("/events/", response_model=List[schemas.Event])
def read_events(db: Session = Depends(deps.get_db), skip: int = 0, limit: int = 100):
    """
    Retrieve a list of upcoming events.
    """
    events = crud_event.get_events(db, skip=skip, limit=limit)
    return events


@router.get("/events/{event_id}", response_model=schemas.Event)
def read_event(*, db: Session = Depends(deps.get_db), event_id: int):
    """
    Get details for a specific event.
    """
    event = crud_event.get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/events/{event_id}/availability", response_model=schemas.EventAvailability)
def read_event_availability(*, db: Session = Depends(deps.get_db), event_id: int):
    """
    Get seat availability for a specific event.
    """
    availability = crud_event.get_event_availability(db, event_id=event_id)
    if availability is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return availability


@router.get("/venues/", response_model=List[schemas.Venue])
def read_venues(db: Session = Depends(deps.get_db), skip: int = 0, limit: int = 100):
    """
    Retrieve all venues.
    """
    venues = crud_event.get_venues(db, skip=skip, limit=limit)
    return venues
