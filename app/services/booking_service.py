from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from loguru import logger

from app.services import cache_service
from app.worker import send_booking_confirmation
from app import models, schemas
from app.crud import crud_event, crud_user
from app.models.event import Event


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

    user = crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ticket_price = 150.00

    try:
        # 1. Create the parent Booking record
        db_booking = models.Booking(user_id=user_id)
        db.add(db_booking)
        db.flush()  # Gets booking.id without committing

        # 2. Create a Ticket for each requested seat
        for seat_id in booking_in.seat_ids:
            db_ticket = models.Ticket(
                price=ticket_price,
                booking_id=db_booking.id,
                event_id=booking_in.event_id,
                seat_id=seat_id,
            )
            db.add(db_ticket)

        # 3. Commit — UniqueConstraint(_event_seat_uc) enforced HERE by PostgreSQL
        db.commit()

        # 4. Re-query with joinedload to fully populate tickets→seat + tickets→event→venue
        db_booking = (
            db.query(models.Booking)
            .options(
                joinedload(models.Booking.tickets).joinedload(models.Ticket.seat),
                joinedload(models.Booking.tickets).joinedload(models.Ticket.event).joinedload(models.Event.venue),
            )
            .filter(models.Booking.id == db_booking.id)
            .first()
        )

        # 5. Invalidate the availability cache for this event
        cache_service.delete_from_cache(f"availability:{booking_in.event_id}")

        # 6. Fire async email confirmation via Celery/RabbitMQ
        send_booking_confirmation.delay(db_booking.id, user.email)

        logger.info(
            f"Booking {db_booking.id} created for user {user_id}, "
            f"event {booking_in.event_id}, seats {booking_in.seat_ids}"
        )
        return db_booking

    except IntegrityError:
        db.rollback()
        logger.warning(
            f"Booking conflict: user {user_id} tried to book "
            f"seats {booking_in.seat_ids} for event {booking_in.event_id} — already taken"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more of the selected seats are already booked.",
        )


def get_my_bookings(db: Session, *, user_id: int) -> list[models.Booking]:
    """
    Returns all bookings for a given user with tickets→seat + tickets→event→venue eagerly loaded.
    """
    return (
        db.query(models.Booking)
        .options(
            joinedload(models.Booking.tickets).joinedload(models.Ticket.seat),
            joinedload(models.Booking.tickets).joinedload(models.Ticket.event).joinedload(models.Event.venue),
        )
        .filter(models.Booking.user_id == user_id)
        .order_by(models.Booking.booking_time.desc())
        .all()
    )
