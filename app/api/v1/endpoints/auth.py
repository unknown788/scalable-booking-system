from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import schemas
from app.crud import crud_user
from app.core.security import verify_password, create_access_token
from app.db import deps
from app.core.config import settings

router = APIRouter()


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = crud_user.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        # Pass email and role
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


