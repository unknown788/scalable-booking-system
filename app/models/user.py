# app/models/user.py
import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class UserRole(enum.Enum):
    customer = "customer"
    organizer = "organizer"


class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.customer)

    bookings = relationship("Booking", back_populates="user")
