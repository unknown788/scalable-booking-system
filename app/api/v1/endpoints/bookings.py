from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app import schemas, models
from app.db import deps
from app.services import booking_service

router = APIRouter()


@router.get("/my", response_model=List[schemas.Booking])
def get_my_bookings(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Get all bookings for the current logged-in user."""
    return booking_service.get_my_bookings(db=db, user_id=current_user.id)


@router.post("/", response_model=schemas.Booking)
def create_booking(
    *,
    db: Session = Depends(deps.get_db),
    booking_in: schemas.BookingCreate,
    current_user: models.User = Depends(deps.get_current_user),
):
    """Create a new booking for the current user. (Any authenticated user)"""
    return booking_service.create_new_booking(
        db=db, booking_in=booking_in, user_id=current_user.id
    )
