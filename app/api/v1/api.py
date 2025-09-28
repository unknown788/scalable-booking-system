# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import resources

api_router = APIRouter()
api_router.include_router(
    resources.router, prefix="/resources", tags=["resources"])
