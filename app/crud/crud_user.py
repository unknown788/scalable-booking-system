# app/crud/crud_user.py
from sqlalchemy.orm import Session
from app.models import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, *, email: str):
    # * enforces keyword-only — get_user_by_email(db, email="x@y.com")
    # prevents accidental positional call get_user_by_email(db, "x@y.com")
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, *, user_in: UserCreate) -> User:
    # Extract raw string from SecretStr — never log or store this
    hashed_password = get_password_hash(user_in.password.get_secret_value())
    db_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        role=user_in.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
