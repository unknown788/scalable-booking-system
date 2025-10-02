from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from app.crud import crud_user
from app.db import deps

router = APIRouter()


@router.post("/signup", response_model=schemas.User)
def register_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
):
    """
    Create new user.
    """
    user = crud_user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = crud_user.create_user(db, user_in=user_in)
    return user
