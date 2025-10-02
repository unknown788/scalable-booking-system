# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import events, public, users, auth , bookings

api_router = APIRouter()


api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(
    # Add bookings router
    bookings.router, prefix="/bookings", tags=["Bookings"])

api_router.include_router(public.router, tags=["Public"])
api_router.include_router(
    events.router, prefix="/organizer", tags=["Organizer"])
