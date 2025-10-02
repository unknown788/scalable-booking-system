from pydantic import BaseModel, EmailStr, SecretStr
from typing import Optional
from app.models import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: SecretStr
    role: UserRole = UserRole.customer  # Default role is customer


class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
