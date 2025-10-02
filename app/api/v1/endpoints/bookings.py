from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas, models
from app.db import deps
from app.services import booking_service

router = APIRouter()


@router.post("/", response_model=schemas.Booking)
def create_booking(
    *,
    db: Session = Depends(deps.get_db),
    booking_in: schemas.BookingCreate,
    current_user: models.User = Depends(deps.get_current_customer)
):
    """
    Create a new booking for the current user. (Customer role required)
    """
    booking = booking_service.create_new_booking(
        db=db, booking_in=booking_in, user_id=current_user.id
    )
    return booking
