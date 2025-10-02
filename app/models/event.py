import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class EventType(enum.Enum):
    movie = "movie"
    concert = "concert"
    meetup = "meetup"

class Event(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    event_time = Column(DateTime, nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    
    venue_id = Column(Integer, ForeignKey("venue.id"))
    venue = relationship("Venue", back_populates="events")

    organizer_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    organizer = relationship("User")

    tickets = relationship("Ticket", back_populates="event")


class Venue(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    rows = Column(Integer, nullable=False)
    cols = Column(Integer, nullable=False)

    events = relationship("Event", back_populates="venue")
    seats = relationship("Seat", back_populates="venue")


class Seat(Base):
    id = Column(Integer, primary_key=True, index=True)
    row = Column(String, nullable=False)
    number = Column(Integer, nullable=False)

    venue_id = Column(Integer, ForeignKey("venue.id"))
    venue = relationship("Venue", back_populates="seats")
    tickets = relationship("Ticket", back_populates="seat")
