# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import events, public, users, auth, bookings, metrics

api_router = APIRouter()

# Auth & Users
api_router.include_router(auth.router,     prefix="/auth",     tags=["Auth"])
api_router.include_router(users.router,    prefix="/users",    tags=["Users"])

# Customer — public read routes (no auth required)
# Mounted without prefix: /api/v1/events/, /api/v1/venues/
api_router.include_router(public.router,   tags=["Public"])

# Customer — booking (auth required, customer role)
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])

# Organizer — write routes (auth required, organizer role)
# Mounted at /organizer: /api/v1/organizer/venues/, /api/v1/organizer/events/
api_router.include_router(events.router,   prefix="/organizer", tags=["Organizer"])

# Observability — live performance metrics (no auth required)
api_router.include_router(metrics.router,  tags=["Metrics"])
