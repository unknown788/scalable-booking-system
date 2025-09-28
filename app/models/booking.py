# app/models/booking.py
import enum
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Enum,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class BookingStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class Booking(Base):
    id = Column(Integer, primary_key=True, index=True)
    booking_time = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(BookingStatus), nullable=False,
                    default=BookingStatus.confirmed)

    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="bookings")

    tickets = relationship(
        "Ticket", back_populates="booking", cascade="all, delete-orphan")


class Ticket(Base):
    id = Column(Integer, primary_key=True, index=True)
    price = Column(Numeric(10, 2), nullable=False)

    booking_id = Column(Integer, ForeignKey("booking.id"))
    booking = relationship("Booking", back_populates="tickets")

    event_id = Column(Integer, ForeignKey("event.id"))
    event = relationship("Event", back_populates="tickets")

    seat_id = Column(Integer, ForeignKey("seat.id"))
    seat = relationship("Seat", back_populates="tickets")

    __table_args__ = (
        UniqueConstraint("event_id", "seat_id", name="_event_seat_uc"),
    )
