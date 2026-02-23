from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from loguru import logger

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    logger.debug("Hashing password for a new user")
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Creates a signed JWT.
    `data` must contain at least {"sub": user.email, "role": user.role.value}
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
