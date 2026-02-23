from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.db import deps
from app.models.user import User
from app.services import event_service

router = APIRouter()


@router.post("/venues/", response_model=schemas.Venue)
def create_new_venue(
    *,
    db: Session = Depends(deps.get_db),
    venue_in: schemas.VenueCreate,
    current_user: User = Depends(deps.get_current_organizer),
):
    """Create a new venue and auto-generate all seats. (Organizer only)"""
    return event_service.create_venue(db=db, venue_in=venue_in)


@router.post("/events/", response_model=schemas.Event)
def create_new_event(
    *,
    db: Session = Depends(deps.get_db),
    event_in: schemas.EventCreate,
    current_user: User = Depends(deps.get_current_organizer),
):
    """Create a new event at a specific venue. (Organizer only)"""
    return event_service.create_event(
        db=db, event_in=event_in, organizer_id=current_user.id
    )
