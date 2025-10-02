from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import schemas
from app.crud import crud_event
from app.db import deps
from app.models.user import User

router = APIRouter()


@router.post("/venues/", response_model=schemas.Venue)
def create_new_venue(
    *,
    db: Session = Depends(deps.get_db),
    venue_in: schemas.VenueCreate,
    current_user: User = Depends(
        deps.get_current_organizer)  # Protect the endpoint
):
    """
    Create a new venue. (Organizer only)
    """
    venue = crud_event.create_venue(db=db, venue_in=venue_in)
    return venue


@router.post("/events/", response_model=schemas.Event)
def create_new_event(
    *,
    db: Session = Depends(deps.get_db),
    event_in: schemas.EventCreate,
    current_user: User = Depends(
        deps.get_current_organizer)  # Protect the endpoint
):
    """
    Create a new event at a specific venue. (Organizer only)
    """
    # We could add validation here to ensure the venue exists
    event = crud_event.create_event(
        db=db, event_in=event_in, organizer_id=current_user.id)
    return event
