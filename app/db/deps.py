# app/db/deps.py
from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError


from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.crud.crud_user import get_user
from app import models

from app.core.config import settings
from app.crud import crud_user
from app.schemas.token import TokenData


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token"
)


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenData(email=payload.get("sub"))
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = crud_user.get_user_by_email(db, email=token_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_organizer(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.organizer:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_current_customer(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role != models.UserRole.customer:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
