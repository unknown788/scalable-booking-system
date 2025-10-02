from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app import models, schemas
from app.crud import crud_event


def create_new_booking(
    db: Session, *, booking_in: schemas.BookingCreate, user_id: int
) -> models.Booking:
    """
    Creates a new booking in an atomic transaction.
    Rolls back if any seat is already booked for the given event.
    """
    event = crud_event.get_event(db, event_id=booking_in.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # For now, let's set a static price. You could extend this to be dynamic.
    ticket_price = 150.00

    # We use a transaction to ensure atomicity
    try:
        # 1. Create the parent Booking record
        db_booking = models.Booking(user_id=user_id)
        db.add(db_booking)
        db.flush()  # Use flush to get the db_booking.id before committing

        # 2. Create a Ticket for each requested seat
        for seat_id in booking_in.seat_ids:
            db_ticket = models.Ticket(
                price=ticket_price,
                booking_id=db_booking.id,
                event_id=booking_in.event_id,
                seat_id=seat_id,
            )
            db.add(db_ticket)

        # 3. Commit the transaction
        db.commit()
        db.refresh(db_booking)
        return db_booking

    except IntegrityError:
        # This block executes if the UniqueConstraint on (event_id, seat_id) fails
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more of the selected seats are already booked.",
        )
